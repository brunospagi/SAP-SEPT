# Use uma versão estável do Python (3.13 não existe ainda - use 3.12)
FROM python:3.12

# Cria o diretório da aplicação
RUN mkdir /app

# Define o diretório de trabalho
WORKDIR /app

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1  
ENV PYTHONUNBUFFERED=1          
ENV DJANGO_SUPERUSER_PASSWORD=2013@Als  

# Atualiza o pip
RUN pip install --upgrade pip

# Copia APENAS o requirements.txt primeiro (para cache de dependências)
COPY requirements.txt /app/

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODOS os arquivos do projeto DEPOIS das dependências
COPY . /app/

# Executa migrações do banco de dados
RUN python manage.py makemigrations
RUN python manage.py makemigrations core
RUN python manage.py migrate

# Cria o superusuário (só funciona se o usuário não existir)
RUN python manage.py createsuperuser --noinput --username admin --email brunospagi@gmail.com

# Expõe a porta do Django
EXPOSE 8000

# Inicia o servidor (APENAS para desenvolvimento)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]