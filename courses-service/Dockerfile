FROM python:3.12-slim
WORKDIR /app
COPY courses-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto/ proto/
COPY courses-service/server.py .
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/courses.proto
EXPOSE 8001 50051
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
