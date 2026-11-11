Arquitetura Atual da EduTech

1. Visão geral

A Prova de Conceito (PoC) da EduTech utiliza uma arquitetura baseada em microsserviços, composta por dois serviços independentes: courses-service e enrollment-service.

A comunicação externa acontece por meio de uma API REST, utilizando o Nginx como API Gateway. Já a comunicação interna entre os microsserviços utiliza gRPC.

A aplicação é executada em contêineres Docker, organizados pelo Docker Compose.

2. Componentes da arquitetura

API Gateway (Nginx): recebe as requisições externas e encaminha cada solicitação ao microsserviço correspondente. Também aplica controle de requisições (rate limiting), timeouts e identificação das requisições por meio do header X-Request-ID.

courses-service: responsável pelo gerenciamento e disponibilização das informações dos cursos, incluindo nomes, identificadores e quantidade de vagas disponíveis. Disponibiliza endpoints REST e um servidor gRPC para comunicação interna.

enrollment-service: responsável pelo gerenciamento das matrículas. Recebe requisições REST e consulta o courses-service por meio de gRPC para verificar a existência do curso e a disponibilidade de vagas.

Docker Compose: responsável por executar e organizar os contêineres dos serviços e do API Gateway, permitindo a comunicação entre eles em uma rede interna.

3. Fluxo de comunicação

O funcionamento da arquitetura ocorre na seguinte sequência:

Requisição do cliente: o estudante realiza uma solicitação à plataforma EduTech, por meio de uma aplicação cliente, utilizando uma requisição HTTP com API REST.

Entrada pelo API Gateway: a requisição chega ao Nginx, que atua como ponto único de entrada da aplicação. O Gateway identifica a rota solicitada e encaminha a requisição ao serviço correspondente.

Encaminhamento aos microsserviços: quando a solicitação envolve cursos, o Gateway encaminha a requisição ao courses-service. Quando envolve matrículas, encaminha ao enrollment-service.

Comunicação interna via gRPC: ao receber uma solicitação de matrícula, o enrollment-service consulta o courses-service utilizando o protocolo gRPC, por meio da operação GetCourse, para verificar os dados do curso e a disponibilidade de vagas.

Mecanismos de resiliência: durante a comunicação entre os microsserviços, são aplicados mecanismos para lidar com falhas e indisponibilidade. O enrollment-service utiliza timeout de 1 segundo, até três tentativas com backoff exponencial e circuit breaker. O API Gateway também aplica timeouts e controle de requisições.

Retorno da resposta: após o processamento, o microsserviço retorna o resultado ao API Gateway, que encaminha a resposta HTTP ao cliente.

4. Mecanismos de resiliência

A PoC implementa mecanismos para aumentar a confiabilidade da comunicação entre os microsserviços:

Timeout: limita o tempo de espera pela resposta do serviço de cursos.

Retry: realiza novas tentativas de comunicação quando ocorre uma falha, utilizando backoff exponencial.

Circuit Breaker: interrompe temporariamente as chamadas quando são identificadas falhas consecutivas, permitindo uma tentativa de recuperação após determinado intervalo.

Rate Limiting: limita a quantidade de requisições recebidas pelo API Gateway.

X-Request-ID: permite identificar e acompanhar as requisições durante o processamento.

5. Considerações finais

A arquitetura atual demonstra os principais conceitos de uma aplicação baseada em microsserviços, utilizando REST para a comunicação externa, gRPC para a comunicação interna, API Gateway para centralizar as requisições e mecanismos de resiliência para lidar com falhas.

Os serviços são executados de forma conteinerizada utilizando Docker Compose.

Nesta versão da PoC, ainda não existe um Service Mesh implementado. A utilização do Istio e do Kubernetes faz parte da proposta de evolução da arquitetura, permitindo adicionar recursos de gerenciamento, segurança e observabilidade à comunicação entre os microsserviços.
