#!/usr/bin/env bash
# Roteiro da demonstração ao vivo. Uso: ./scripts/demo.sh   (com `docker compose up -d --build` rodando)
BASE=http://localhost:8081/api
pause() { echo; read -rp "[Enter para continuar] " _; echo; }
post() { curl -s -X POST $BASE/enrollments -H 'Content-Type: application/json' -H "Idempotency-Key: $1" -d "$2"; echo; }

echo "1) Listar cursos (REST via API Gateway)"; curl -s $BASE/courses; echo; pause

echo "2) Criar matrícula (REST -> enrollment -> gRPC -> courses)"
post demo-001 '{"student_id":"igor","course_id":"AS201"}'; pause

echo "3) Repetir a MESMA requisição: idempotência (mesmo id, sem duplicar)"
post demo-001 '{"student_id":"igor","course_id":"AS201"}'; pause

echo "4) Curso inexistente (404) e curso lotado (409)"
post demo-002 '{"student_id":"igor","course_id":"XXX"}'
post demo-003 '{"student_id":"igor","course_id":"LP001"}'; pause

echo "5) Derrubar o courses-service e tentar matricular (falha isolada, 503 controlado)"
docker compose stop courses-service
for i in 1 2 3 4; do
  curl -s -o /dev/null -w "tentativa $i -> HTTP %{http_code}\n" -X POST $BASE/enrollments \
    -H 'Content-Type: application/json' -H "Idempotency-Key: fail-$i" -d '{"student_id":"igor","course_id":"AS201"}'
done
echo "Estado do circuit breaker:"
docker compose exec enrollment-service python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8002/circuit').read().decode())"
pause

echo "6) Subir o courses-service de novo: o circuito fecha sozinho após ~10s"
docker compose start courses-service; sleep 12
post demo-004 '{"student_id":"igor","course_id":"AS201"}'
echo "Notificação assíncrona nos logs:  docker compose logs enrollment-service | grep NOTIFICAÇÃO"
