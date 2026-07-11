Entendido! Você quer um arquivo **`REASONIX.md`** (provavelmente uma brincadeira com "Reasoning + X" ou "Execution") que seja ainda **mais direto, operacional e "mão na massa"** do que o `reasoning.md` anterior.

Enquanto o `reasoning.md` é o mapa rodoviário (arquitetura), o **`REASONIX.md`** será o **"Manual de Instruções do Robô"**. Ele não explica *por que* estamos fazendo, mas sim **O QUE** o agente deve codificar, **EM QUAL ORDEM**, e **QUAL É O PROMPT EXATO** para cada etapa.

Aqui está o arquivo pronto para você salvar como `REASONIX.md` e entregar ao seu agente (Cursor/Devin/ChatGPT) dizendo: *"Siga este arquivo à risca, etapa por etapa, e não avance para a próxima sem confirmar que a anterior funciona."*

---

# `REASONIX.md` — Plano de Execução Síncrona para o Agente

> **Regra de Ouro:** Execute os passos em ordem sequencial. Não pule etapas. Ao final de cada fase, **rode a aplicação** e verifique se a rota específica está funcionando antes de prosseguir.

---

## FASE 0: FUNDAÇÃO (Setup e Configuração)
*Objetivo: Estrutura de pastas, dependências e primeira execução do FastAPI.*

### Tarefa 0.1: Estrutura de Pastas
Crie exatamente esta árvore no diretório raiz do projeto:
```text
/app/
    /core/
    /models/
    /schemas/
    /services/
    /routers/
    /templates/
    /static/
    /uploads/
/instance/
.env
requirements.txt
```

### Tarefa 0.2: Dependências (`requirements.txt`)
Salve este conteúdo:
```text
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
aiosqlite==0.20.0
async-exit-stack==1.0.1
async-generator==1.10
python-multipart==0.0.12
httpx==0.27.0
jinja2==3.1.4
python-dotenv==1.0.1
bcrypt==4.2.0
passlib==1.7.4
PyPDF2==3.0.1
Pillow==10.4.0
pdf2image==1.16.3
aiofiles==24.1.0
```

### Tarefa 0.3: Variáveis de Ambiente (`.env`)
Crie o arquivo `.env` com:
```env
DEEPSEEK_API_KEY="sk-..."
SECRET_KEY="sua_chave_super_secreta_32_bytes"
DATABASE_URL="sqlite+aiosqlite:///./instance/app.db"
```

### Tarefa 0.4: Arquivo de Configuração (`core/config.py`)
Crie a classe `Settings` herdando de `BaseSettings` para ler as variáveis do `.env`.  
**Prompt para o agente:** *"Crie um Pydantic Settings com os campos acima e configure o load_dotenv()."*

### Tarefa 0.5: Entrypoint (`main.py`)
Crie o app FastAPI, configure o `Jinja2Templates` (pasta `templates`), `StaticFiles` (pasta `static`) e inclua os routers (mesmo que ainda estejam vazios).  
**Prompt para o agente:** *"Configure o FastAPI com lifespan para criar as tabelas do banco ao iniciar. Rode com uvicorn e verifique se acessar `/docs` mostra a documentação."*

---

## FASE 1: BANCO DE DADOS E MODELOS (SQLAlchemy Async)
*Objetivo: Conectar ao SQLite e criar as 3 tabelas.*

### Tarefa 1.1: Database Core (`core/database.py`)
Implemente:
- `AsyncEngine` (usando `DATABASE_URL`).
- `async_sessionmaker`.
- Dependência `async def get_db()` para injetar a sessão nas rotas.

### Tarefa 1.2: Models (`models/models.py`)
Crie as classes **exatamente** com os campos definidos no PRD (`User`, `Essay`, `Correction`).  
*Dica:* Use `sqlalchemy.orm.Mapped` e `mapped_column` para type hints modernos.

**Prompt para o agente:** *"Crie os modelos usando AsyncAttrs. Defina as foreign keys e relacionamentos. Após criar, rode `async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)` no main.py."*

### Tarefa 1.3: Schemas Pydantic (`schemas/schemas.py`)
Crie schemas de leitura/escrita para:
- `UserCreate`, `UserLogin`.
- `EssayCreate`, `EssayOut`.
- `CorrectionOut`.

---

## FASE 2: AUTENTICAÇÃO E SESSÃO (Login/Register)
*Objetivo: Proteger as rotas e gerenciar usuários via cookies.*

### Tarefa 2.1: Middleware de Sessão
No `main.py`, adicione `SessionMiddleware` do Starlette com o `SECRET_KEY`.

### Tarefa 2.2: Dependência de Segurança (`core/dependencies.py`)
Crie `async def get_current_user(request: Request, db: AsyncSession = Depends(get_db))`:  
- Busca `user_id` no `request.session`.
- Se não existir, levanta `HTTPException(403)`.
- Retorna o objeto `User` do banco.

### Tarefa 2.3: Router de Auth (`routers/auth.py`)
Crie as rotas:
- `GET /login` -> Renderiza `login.html`.
- `GET /register` -> Renderiza `register.html`.
- `POST /register` -> Hash da senha (bcrypt), salva no banco, redireciona para `/login`.
- `POST /login` -> Verifica senha, salva `session['user_id'] = user.id`, redireciona para `/dashboard`.
- `GET /logout` -> `session.clear()`, redireciona para `/login`.

**Prompt para o agente:** *"Use templates Jinja2 com Bootstrap 5 para login e register. Coloque mensagens de flash para erros."*

---

## FASE 3: UPLOAD E OCR (Entrada de Dados)
*Objetivo: Implementar a tela de upload com duas abas e a revisão humana.*

### Tarefa 3.1: Router de Upload (`routers/upload.py`)
- `GET /upload` (protegido por `Depends(get_current_user)`).
- `POST /upload/text`: Recebe formulário com `raw_text`. Salva `Essay(status='pending_correction', source_type='pasted')`. Redireciona para `/correction/start/{id}`.
- `POST /upload/file`: Recebe `UploadFile`. Salva em `/uploads`. Extrai texto chamando o serviço de OCR (Tarefa 3.2). Cria `Essay(status='pending_review')`. Redireciona para `/review/{id}`.

### Tarefa 3.2: Serviço de OCR (`services/ocr_service.py`)
Crie `async def extract_text_from_image(file_path: str) -> str`:  
1. Abre a imagem com Pillow.
2. Converte para Base64.
3. Monta payload para a DeepSeek (modelo `deepseek-chat` com mensagem contendo `image_url`).
4. Retorna o texto extraído. **Trate erros de API para não quebrar o fluxo.**

### Tarefa 3.3: Tela de Revisão (`/review/{essay_id}`)
- `GET`: Renderiza `review.html` com `<textarea>` contendo o `raw_text` extraído e um botão "Confirmar e Corrigir".
- `POST`: Atualiza o `raw_text` do Essay com o valor do formulário. Muda status para `'pending_correction'`. Redireciona para `/correction/start/{id}`.

**Prompt para o agente:** *"Crie um template review.html com Bootstrap. O textarea deve ter 20 linhas. Adicione um botão 'Voltar' para /upload."*

---

## FASE 4: CORREÇÃO DUAL E RESULTADOS (O CORAÇÃO)
*Objetivo: Chamar a IA duas/três vezes, salvar e mostrar o resultado.*

### Tarefa 4.1: Serviço de Correção (`services/correction_service.py`)
Crie `async def call_deepseek_corrector(text: str, type: str, temp: float) -> dict`:
- Defina os **System Prompts** (A, B, C) exatamente como listados no `reasoning.md`.
- Use `httpx.AsyncClient` para chamar a API.
- Faça `json.loads()` na resposta (trate se vier com ```json).

Crie `async def perform_full_correction(essay_id: int, text: str, db: AsyncSession)`:
1. Roda `call_deepseek_corrector` para A e B com `asyncio.gather`.
2. Salva ambos no banco (duas linhas em `Correction`).
3. Verifica diferença de `total_score`.
4. Se diferença > 100, chama o C.
5. Calcula `final_score` (média dos mais próximos).
6. Atualiza `Essay.final_score` e `Essay.status = 'completed'`.

### Tarefa 4.2: Router de Correção (`routers/correction.py`)
- `GET /correction/start/{essay_id}`:
  - Busca Essay, verifica se `status == 'pending_correction'`.
  - Dispara `perform_full_correction`.
  - Redireciona para `GET /result/{essay_id}`.

### Tarefa 4.3: Página de Resultado (`/result/{essay_id}`)
- Busca o Essay e todas as Corrections associadas.
- Renderiza `result.html` com:
  - **Layout de 2 colunas** (A e B).
  - Se houver C, exibe um banner de alerta e mostra a nota oficial.
  - Em cada coluna: Nota Total, Barras de Progresso para C1 a C5 (com valores 0-200), e o `feedback_json` parseado em um accordion.

### Tarefa 4.4: Dashboard (`/dashboard`)
- `GET /dashboard`: Lista **todos** os Essays do usuário logado, ordenados por `created_at` decrescente.
- Colunas: Data, Tipo (ícone), Nota Final, Status (badge).
- Botão "Nova Correção" linkando para `/upload`.

---

## FASE 5: EXTRAS E POLIMENTO (Opcional mas Valoriza)

### Tarefa 5.1: Estatísticas (`/stats`)
- Use Chart.js (CDN) no template.
- Busque todas as correções do usuário e plote a evolução da média de C1, C2, C3, C4, C5 ao longo do tempo.

### Tarefa 5.2: Tratamento de Erros Globais
- Adicione `@app.exception_handler(HTTPException)` para renderizar templates de erro personalizados (404, 500).
- Se a API da DeepSeek falhar durante a correção, capture, mude status para `'failed'` e exiba um botão "Tentar Novamente" no Dashboard.

### Tarefa 5.3: Segurança de Upload
- Valide extensões: `.pdf`, `.jpg`, `.jpeg`, `.png`.
- Limite de tamanho: 10MB (use `aiofiles` para ler em chunks e validar).
Adicione uma nova FASE 6 (ou insira antes da FASE 4) para implementar o CRUD e a integração.

##  FASE 6: Gerenciamento de Competências e Templates
### Tarefa 6.1: Modelos (já descritos acima)
### Tarefa 6.2: Seed inicial – ao criar as tabelas, insira as 5 competências padrão do ENEM e um template "ENEM Oficial" associado a elas.
### Tarefa 6.3: Rotas CRUD para competências (protegidas por Depends(get_current_user)):

GET /competences – listar todas (com filtro por usuário ou globais)

POST /competences – criar nova

PUT /competences/{id} – editar

DELETE /competences/{id} – excluir (apenas se não estiver em uso)

Tarefa 6.4: Rotas CRUD para templates:

GET /templates – listar

POST /templates – criar (com seleção de competências via checkboxes)

PUT /templates/{id} – editar (reassociar competências)

DELETE /templates/{id} – excluir

### Tarefa 6.5: Atualizar a tela de upload (upload.html) para incluir um <select> com os templates do usuário (e um padrão).
### Tarefa 6.6: Modificar o serviço de correção para receber o template_id do Essay e usar as competências associadas.
### Tarefa 6.7: Atualizar a tela de resultado (result.html) para exibir as notas e justificativas de forma dinâmica, iterando sobre o scores_json.

### Tarefa 6.8: (Opcional) Permitir que o professor defina um template padrão por usuário (campo default_template_id no User).

📝 Exemplo de Prompt Gerado Dinamicamente
text
Corrija a redação abaixo de acordo com as seguintes competências:

1. Competência 1: Domínio da norma padrão (0 a 200)
2. Competência 2: Compreensão do tema (0 a 200)
3. Competência 3: Repertório sociocultural (0 a 200)
4. Competência 4: Coesão textual (0 a 200)
5. Competência 5: Proposta de intervenção (0 a 200)

Para cada competência, retorne um objeto JSON com 'nota' e 'justificativa'.
Retorne APENAS JSON válido, sem markdown, no formato:
{"comp_1": {"nota": int, "justificativa": "..."}, ... , "total": int}

Redação:
[texto do aluno]
🔄 Compatibilidade com Dados Antigos
Caso você já tenha redações corrigidas com as colunas c1..c5, sugiro uma migração que:

Adicione scores_json como campo JSON (pode ser NULL).

Para registros antigos, preencha scores_json com um objeto gerado a partir dos campos c1..c5 (assim você unifica).

Gradualmente, passe a usar apenas o JSON.


---

## INSTRUÇÃO FINAL PARA O AGENTE

> *"Ao final de cada FASE, pare e me entregue um resumo do que foi feito. Eu testarei manualmente a rota correspondente. Somente quando eu disser 'OK, próxima fase', você deve avançar. Mantenha todo o código em inglês (nomes de variáveis/funções), mas os textos dos prompts da IA e as mensagens da UI em **Português do Brasil**."*

---

Agora você tem um `REASONIX.md` cirúrgico. O agente não tem mais desculpas para "achar" o que fazer — ele só precisa executar essas tarefas em sequência. Mande ver! 🚀