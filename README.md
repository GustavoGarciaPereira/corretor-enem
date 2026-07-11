# 📝 Correção de Redação

Sistema web para correção de redações no formato ENEM utilizando inteligência artificial (DeepSeek), com suporte a correção dupla, templates personalizáveis e níveis de desempenho.

## ✨ Funcionalidades

### 📄 Upload de Redações
- **Texto colado**: digite ou cole a redação diretamente
- **Arquivo**: upload de PDF, JPG ou PNG (OCR via DeepSeek vision)

### 🤖 Correção por IA (DeepSeek V4)
- **Correção Dupla**: dois corretores IA (A e B) avaliam a redação em paralelo
- **Desempate (C)**: se a diferença entre A e B for > 100 pontos, um terceiro corretor é acionado
- **Níveis de Desempenho**: a IA escolhe entre 6 níveis (0 a 5) com pontuações fixas (0, 40, 80, 120, 160, 200), alinhado ao modelo oficial do ENEM
- **Mock automático**: funciona sem chave de API para desenvolvimento

### 📋 Gestão de Competências e Templates
- **Competências personalizáveis**: crie, edite e exclua competências com descrições próprias
- **Níveis por competência**: cada competência tem 6 níveis com pontuação fixa e descrição qualitativa
- **Templates**: agrupe competências em templates de correção reutilizáveis
- **Padrão ENEM**: já vem com as 5 competências oficiais e 6 níveis cada

### 👤 Autenticação
- Cadastro e login com sessão via cookies
- Cada usuário vê apenas suas próprias redações, competências e templates

### 📊 Dashboard e Estatísticas
- Dashboard com lista de redações, notas finais e scores por corretor
- Página de resultado com progress bars, feedback em accordion e badge do nível
- Estatísticas com gráficos Chart.js (evolução das notas por competência)

## 🚀 Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Templates | Jinja2 + Bootstrap 5 |
| Banco | SQLite via SQLAlchemy 2.0 |
| IA | DeepSeek API (deepseek-v4-flash) |
| OCR | PyPDF2 + pdf2image + DeepSeek vision |
| Gráficos | Chart.js |
| Autenticação | Sessão via cookies + bcrypt |

## 📦 Instalação

```bash
# Clone o repositório
git clone <url>
cd correcao_redacao

# Crie e ative o virtual environment
python3 -m venv venv
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com sua chave da DeepSeek
```

## ⚙️ Configuração

Edite o arquivo `.env`:

```env
DEEPSEEK_API_KEY="sk-sua-chave-aqui"
SECRET_KEY="sua_chave_secreta_32_bytes"
DEEPSEEK_MODEL="deepseek-v4-flash"
```

> **Sem chave de API?** O sistema funciona em modo **mock**, gerando correções simuladas para testes.

## ▶️ Execução

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

Acesse: **http://127.0.0.1:8000**

## 🧪 Primeiros Passos

1. Acesse `/register` e crie um usuário
2. Faça login em `/login`
3. Vá em **Admin → Competências** para ver as competências padrão do ENEM
4. Vá em **Admin → Templates** para ver o template "ENEM Oficial"
5. Clique em **Nova Correção** no dashboard
6. Cole um texto ou envie um arquivo e escolha o template
7. Aguarde a correção e veja o resultado

## 📁 Estrutura do Projeto

```
correcao_redacao/
├── app/
│   ├── main.py                 # Entrypoint FastAPI
│   ├── core/
│   │   ├── config.py           # Configurações (.env)
│   │   ├── database.py         # SQLAlchemy engine + sessão
│   │   ├── dependencies.py     # Dependências compartilhadas
│   │   ├── seed.py             # Seed de dados padrão
│   │   └── templates_setup.py  # Config Jinja2 + filtros
│   ├── models/
│   │   └── models.py           # User, Essay, Correction, Competence, Template, Level
│   ├── schemas/
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/
│   │   ├── correction_service.py  # Lógica de correção por IA
│   │   └── ocr_service.py         # OCR para PDFs e imagens
│   ├── routers/
│   │   ├── auth.py             # Login, registro
│   │   ├── upload_router.py    # Upload de redações + revisão
│   │   ├── correction_router.py # Gatilho de correção
│   │   ├── page_router.py      # Dashboard, resultado, estatísticas
│   │   ├── competence_router.py # CRUD de competências + níveis
│   │   └── template_router.py  # CRUD de templates
│   └── templates/              # Jinja2 HTML
│       ├── base.html           # Layout base com navbar
│       ├── login.html / register.html
│       ├── dashboard.html
│       ├── upload.html
│       ├── review.html
│       ├── result.html
│       ├── stats.html
│       ├── competences.html / competence_form.html
│       ├── templates.html / template_form.html
│       └── error.html
├── instance/                   # Banco SQLite (gitignored)
└── requirements.txt
```

## 🔌 API de Correção

O sistema usa a API da DeepSeek. O prompt da IA lista todas as competências do template com seus 6 níveis, e a IA retorna JSON com o nível escolhido para cada competência:

```json
{
  "comp_1": {"level": 4, "justificativa": "..."},
  "comp_2": {"level": 3, "justificativa": "..."},
  "total": 560
}
```

O `total` é **recalculado no backend** somando os scores dos níveis escolhidos.

## 📄 Licença

Projeto educacional.
