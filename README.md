# Proyecto BookStore: Aplicación Escalable en AWS y Microservicios

Este repositorio contiene todo el trabajo realizado para el **Proyecto 2 – Aplicación Escalable** de la materia ST0263 (Tópicos Especiales en Telemática, 2025-1) en la Universidad EAFIT. El objetivo es transformar una **aplicación monolítica BookStore** en una solución escalable en AWS, y finalmente en una arquitectura de **microservicios sobre Kubernetes**.

> **Descripción original del monolito**  
> La app BookStore permite a usuarios publicar y vender libros de segunda mano. Gestiona usuarios, catálogo, compras, pagos y envíos simulados. Actualmente corre en 2 contenedores Docker (Flask + MySQL) orquestados con Docker Compose :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}.

---

## 📋 Índice

1. [Objetivo 1: Despliegue en VM única (20%)](#objetivo-1)
2. [Objetivo 2: Escalamiento con VM y servicios AWS (30%)](#objetivo-2)
3. [Objetivo 3: Reingeniería en microservicios + Kubernetes (50%)](#objetivo-3)
4. [Estructura del repositorio](#estructura)
5. [Cómo ejecutar cada etapa](#ejecucion)
6. [Créditos y Licencia](#licencia)

---

## 🎯 Objetivo 1: Despliegue en VM única (20%)

Desplegar la aplicación monolítica en **una sola instancia EC2 Ubuntu**, con:

- **Docker & Docker Compose**  
- **NGINX** como proxy inverso  
- **Certbot/Let’s Encrypt** para HTTPS  
- **Dominio propio** apuntado a la IP de EC2  

### 🛠 Pasos principales

1. **Crear EC2 (Ubuntu 22.04)**  
   - t2.micro, Security Group: puertos 22, 80, 443  
   - Elastic IP asignada  

2. **Instalar dependencias**  
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx unzip
   sudo usermod -aG docker $USER && newgrp docker
   ```
3. Subir y descomprimir el proyecto
   ```bash
   scp -i clave.pem Proyecto.zip ubuntu@IP:/home/ubuntu
   unzip Proyecto.zip && cd BookStore-monolith
   ```
4. Docker Compose
   - docker-compose.yml con servicios db (MySQL 8) y flaskapp (Python Flask)
   - docker-compose up -d --build
     
5. Configurar NGINX
   en nginx
   ````bash
   server {
         listen 80;
         server_name tunombre.dominio.tld;
         location / { proxy_pass http://localhost:5000; … }
   }
   ````
   ````bash
   sudo ln -s /etc/nginx/sites-available/bookstore /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ````

6. Certificado SSL
   ````bash
   sudo certbot --nginx -d tunombre.dominio.tld
   sudo certbot renew --dry-run
   ````
   Resultado: https://tunombre.dominio.tld con candado HTTPS, app Flask ↔ MySQL en contenedores Docker.

##  Objetivo 2: Escalamiento con VM y servicios AWS

Escalar horizontalmente el monolito en AWS:
- Auto Scaling Group con mínimo 2 y máximo 5 instancias
- Application Load Balancer (ALB) público
- Base de datos externa con alta disponibilidad en EC2 (Master/Replica + HAProxy)
- Sistema de archivos compartido con NFS → Amazon EFS

**Infraestructura y pasos**
1. Crear AMI personalizada
   - Desde la EC2 del Objetivo 1, detener contenedores y “Create Image” en AWS Console.

2. Launch Template
  - AMI: la creada
  - User-data (opcional) para docker-compose up -d
  - Auto-assign Public IP: Enabled

3. Auto Scaling Group
  - AZs: us-east-1a, us-east-1b
  - Template: el anterior
  - Desired = Min = 2, Max = 5
  - Scaling policy: Target Tracking CPU 50%

4. Application Load Balancer
  - Scheme: internet-facing
  - Listeners: HTTP 80 → Target Group; HTTPS 443 (ACM cert) → Target Group
  - Target Group: Protocolo HTTP, Puerto 5000; Health Check GET /ping

5. Servidor NFS / EFS
  - Opción recomendada: Amazon EFS multi-AZ
  - En cada EC2:

  ````bash
  sudo apt install -y nfs-common
  sudo mount -t nfs4 -o nfsvers=4.1 EFS_DNS:/ /mnt/efs
  ````

  - Montar /app/static o carpeta de uploads
  
  6. Base de datos con alta disponibilidad (sin RDS)
  - db-master (10.0.0.137) y db-replica (10.0.0.148) en EC2  
  - MySQL config: bind-address = 0.0.0.0, server-id = 1/2, log_bin y relay-log
  - Usuario de réplica con plugin mysql_native_password
  - Iniciar replication → SHOW SLAVE STATUS muestra Slave_IO_Running: Yes y Seconds_Behind_Master: 0
  - HAProxy (10.0.0.142) frontal TCP 3306

    ````bash
    frontend mysql_front
      bind *:3306
      mode tcp
      default_backend mysql_back
  
    backend mysql_back
      mode tcp
      server db1 10.0.0.137:3306 check
      server db2 10.0.0.148:3306 check backup
    ````
    Ajustar max_connect_errors, FLUSH HOSTS, reglas de SG entre instancias

**Resultado:**
- Cliente → ALB → EC2 (Docker monolito)
- EC2 ↔ EFS ↔ HAProxy → MySQL Master/Replica


## Objetivo 3: Reingeniería en microservicios + Kubernetes

1. Convertir el monolito en 3 microservicios desplegados sobre Kubernetes con un Ingress Controller y Horizontal Pod Autoscaler diferenciados:
- Auth Service (auth-service, puerto 5001)
- Registro/login/logout
- Generación de JWT (/api/login)
- Rutas visuales con Flask-Login (/login, /register)

2. Catalog Service (catalog-service, puerto 5002)
- CRUD de libros
- Endpoints JSON:
  ````bash
  GET /api/book/<id>
  GET /api/my_books      # protegido con JWT
  POST /api/add_book     # protegido con JWT
  PUT /api/edit_book/<id>
  DELETE /api/delete_book/<id>
  ````

3. Order Service (order-service, puerto 5003)
- Compra, pago, entrega
- Consulta a Catalog Service vía HTTP (/api/book/<id>)
- Protección JWT con decorador @token_required
- Persistencia en su propia base (puede compartir la misma MySQL/EFS)

### Despliegue en Kubernetes
- Dockerfiles para cada servicio
- Manifests:
  - deployment.yaml con replicas: N
  - service.yaml (ClusterIP)
  - hpa.yaml (autoscale según CPU o RPS)

- Ingress Controller (NGINX):
  ````bash
  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: bookstore-ingress
    annotations:
      nginx.ingress.kubernetes.io/rewrite-target: /$1
  spec:
    rules:
    - http:
        paths:
        - path: /auth(/|$)(.*)
          pathType: Prefix
          backend: { service: auth-service, port: 5001 }
        - path: /book(/|$)(.*)
          pathType: Prefix
          backend: { service: catalog-service, port: 5002 }
        - path: /order(/|$)(.*)
          pathType: Prefix
          backend: { service: order-service, port: 5003 }
  ````
  Cert-Manager o ACM + DNS Challenge para TLS automático
**Resultado: Arquitectura de microservicios, escalable y aislada, con entrada única vía Ingress.**

### Estructura del Repositorio
````bash
.
├── auth-service/
│   ├── app.py
│   ├── controllers/auth_controller.py
│   ├── models/user.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── catalog-service/
│   ├── app.py
│   ├── controllers/book_controller.py
│   ├── models/book.py
│   ├── templates/
│   ├── requirements.txt
│   └── Dockerfile
│
├── order-service/
│   ├── app.py
│   ├── controllers/purchase_controller.py
│   ├── controllers/payment_controller.py
│   ├── controllers/delivery_controller.py
│   ├── models/purchase.py
│   ├── models/payment.py
│   ├── models/delivery.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── k8s/
│   ├── auth-deployment.yaml
│   ├── catalog-deployment.yaml
│   ├── order-deployment.yaml
│   ├── auth-service.yaml
│   ├── catalog-service.yaml
│   ├── order-service.yaml
│   ├── auth-hpa.yaml
│   ├── catalog-hpa.yaml
│   ├── order-hpa.yaml
│   └── ingress.yaml
│
└── README.md        # ← Este archivo
````

   
