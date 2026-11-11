"""courses-service: expõe REST (porta 8001, usado pelo gateway) e gRPC (porta 50051, uso interno)."""
import os
import time
from concurrent import futures
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException

import courses_pb2
import courses_pb2_grpc

# "Banco de dados" em memória (suficiente para a PoC)
COURSES = {
    "ES101": {"name": "Engenharia de Software", "seats": 30},
    "AS201": {"name": "Arquitetura de Software", "seats": 25},
    "BD301": {"name": "Banco de Dados", "seats": 20},
    "LP001": {"name": "Turma lotada (para testar HTTP 409)", "seats": 0},
}

# Latência artificial para simular lentidão (teste de timeout): LATENCY_MS=1500
LATENCY_MS = int(os.getenv("LATENCY_MS", "0"))


class CourseService(courses_pb2_grpc.CourseServiceServicer):
    def GetCourse(self, request, context):
        time.sleep(LATENCY_MS / 1000)
        course = COURSES.get(request.id)
        if course is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "curso não encontrado")
        return courses_pb2.Course(id=request.id, name=course["name"], seats_available=course["seats"])

    def ListCourses(self, request, context):
        items = [
            courses_pb2.Course(id=cid, name=c["name"], seats_available=c["seats"])
            for cid, c in COURSES.items()
        ]
        return courses_pb2.ListCoursesResponse(courses=items)


@asynccontextmanager
async def lifespan(app: FastAPI):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    courses_pb2_grpc.add_CourseServiceServicer_to_server(CourseService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    yield
    server.stop(grace=1)


app = FastAPI(title="courses-service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/courses")
def list_courses():
    return [{"id": cid, "name": c["name"], "seats_available": c["seats"]} for cid, c in COURSES.items()]


@app.get("/courses/{course_id}")
def get_course(course_id: str):
    c = COURSES.get(course_id)
    if c is None:
        raise HTTPException(status_code=404, detail="curso não encontrado")
    return {"id": course_id, "name": c["name"], "seats_available": c["seats"]}
