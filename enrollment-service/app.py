"""enrollment-service: API REST de matrículas. Consulta o courses-service via gRPC com
timeout, retry com backoff exponencial e circuit breaker. Notificações são assíncronas (fila)."""
import logging
import os
import queue
import threading
import time
import uuid
from typing import Optional

import grpc
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

import courses_pb2
import courses_pb2_grpc
from resilience import CircuitBreaker, CircuitOpenError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("enrollment")

app = FastAPI(title="enrollment-service")

channel = grpc.insecure_channel(os.getenv("COURSES_GRPC", "courses-service:50051"))
stub = courses_pb2_grpc.CourseServiceStub(channel)
breaker = CircuitBreaker(failure_threshold=3, reset_timeout=10)

ENROLLMENTS: dict = {}
IDEMPOTENCY: dict = {}
LOCK = threading.Lock()
NOTIFY_QUEUE: "queue.Queue[dict]" = queue.Queue()


class CourseNotFound(Exception):
    pass


class EnrollmentRequest(BaseModel):
    student_id: str
    course_id: str


def get_course(course_id: str):
    """Chamada gRPC com timeout de 1s e até 3 tentativas (backoff 0.1s, 0.2s, 0.4s)."""
    last_error = None
    for attempt in range(3):
        try:
            return stub.GetCourse(courses_pb2.GetCourseRequest(id=course_id), timeout=1.0)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise CourseNotFound(course_id)
            last_error = e
            log.warning("falha ao consultar cursos (tentativa %d): %s", attempt + 1, e.code())
            time.sleep(0.1 * 2 ** attempt)
    raise last_error


def notification_worker():
    """Consumidor em segundo plano: simula envio lento de e-mail sem atrasar a matrícula."""
    while True:
        event = NOTIFY_QUEUE.get()
        time.sleep(2)
        log.info("NOTIFICAÇÃO enviada: %s", event)


threading.Thread(target=notification_worker, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/circuit")
def circuit():
    return {"state": breaker.state, "failures": breaker.failures}


@app.post("/enrollments", status_code=201)
def create_enrollment(
    body: EnrollmentRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Header Idempotency-Key é obrigatório")
    req_id = request.headers.get("x-request-id", "-")

    with LOCK:
        if idempotency_key in IDEMPOTENCY:
            log.info("[%s] requisição repetida (key=%s): devolvendo resultado anterior", req_id, idempotency_key)
            return IDEMPOTENCY[idempotency_key]

    try:
        course = breaker.call(get_course, body.course_id, ignore=(CourseNotFound,))
    except CourseNotFound:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Serviço de cursos indisponível (circuito aberto). Tente novamente em instantes.")
    except grpc.RpcError:
        raise HTTPException(status_code=503, detail="Serviço de cursos indisponível.")

    if course.seats_available <= 0:
        raise HTTPException(status_code=409, detail="Sem vagas disponíveis")

    enrollment = {
        "id": str(uuid.uuid4()),
        "student_id": body.student_id,
        "course_id": body.course_id,
        "course_name": course.name,
        "status": "CONFIRMED",
    }
    with LOCK:
        ENROLLMENTS[enrollment["id"]] = enrollment
        IDEMPOTENCY[idempotency_key] = enrollment
    NOTIFY_QUEUE.put({"type": "EnrollmentConfirmed", "enrollment_id": enrollment["id"], "student_id": body.student_id})
    log.info("[%s] matrícula %s confirmada", req_id, enrollment["id"])
    return enrollment


@app.get("/enrollments/{enrollment_id}")
def get_enrollment(enrollment_id: str):
    e = ENROLLMENTS.get(enrollment_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    return e
