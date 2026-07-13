# 📄 PRD – Plataforma de Correção Dual de Redações com IA (ENEM e Vestibulares)

**Versão:** 2.0 (Final)  
**Data:** Julho de 2026  
**Autor:** Product Owner / Arquiteto de Soluções  

---

## 1. Introdução e Objetivo Estratégico

### 1.1 Contexto
O Exame Nacional do Ensino Médio (ENEM) é a principal porta de entrada para o ensino superior no Brasil. A redação, com peso significativo na nota final, é corrigida por **dois corretores humanos independentes**. Se a diferença entre as notas for superior a 100 pontos, um **terceiro corretor** é acionado para desempate. Esse modelo garante isenção, mas é caro, demorado e subjetivo.

Professores e cursinhos precisam simular esse ambiente para treinar seus alunos, mas enfrentam dois gargalos:
1. **Tempo:** Corrigir manualmente dezenas de redações por semana é inviável.
2. **Fidelidade:** Uma única IA (ou um único professor) não replica a dinâmica de dois corretores com perfis diferentes.

### 1.2 Proposição de Valor
Oferecer uma plataforma web que:
- **Simula a correção oficial do ENEM** com dois corretores de IA com perfis opostos (Rigoroso x Progressista), aplicando a **regra do terceiro corretor** automaticamente.
- **Garante precisão na entrada** com OCR de imagens/PDFs seguido de revisão humana obrigatória.
- **Empodera o professor** com um sistema de **Competências Dinâmicas** (CRUD), permitindo criar templates de correção para qualquer vestibular (ENEM, Fuvest, Unicamp, vestibulares militares, etc.), sem depender de atualizações do sistema.

### 1.3 Objetivos de Negócio (OKRs)
| Objetivo | Métrica | Meta |
| :--- | :--- | :--- |
| **Precisão** | Correlação entre nota da IA e nota de um corretor humano experiente | ≥ 95% (diferença média < 20 pontos) |
| **Produtividade** | Tempo médio do upload da redação até a entrega do resultado final | < 3 minutos (para redações digitalizadas) |
| **Adoção** | Número de professores ativos (MAU) no primeiro mês | 50 professores |
| **Flexibilidade** | Templates criados pelos usuários | Média de 2 templates por professor ativo |

---

## 2. Público-Alvo e Personas

| Persona | Perfil | Dores | Ganhos |
| :--- | :--- | :--- | :--- |
| **João (Professor Particular)** | Dá aulas para 10–15 alunos. Corrige redações manualmente aos finais de semana. | Falta de tempo; feedbacks genéricos; dificuldade em rastrear evolução por competência. | Correção instantânea; feedback detalhado competência a competência; dashboard de evolução. |
| **Carla (Coordenadora de Cursinho)** | Gerencia 50+ alunos e uma equipe de 5 professores. Precisa de dados para planejar aulas. | Dificuldade em padronizar a correção entre os professores; falta de dados estatísticos consolidados. | Relatórios agregados; identificação rápida das competências mais deficitárias da turma; correção padronizada pela IA. |
| **Marcos (Aluno Autodidata)** | Estuda sozinho e quer treinar redações. | Não tem quem corrija com o rigor do ENEM. | Correção gratuita (ou de baixo custo) e feedbacks estruturados para evolução. |

---

## 3. Jornada do Usuário (User Flow)

| Etapa | Ação do Usuário | Sistema | Fluxo de Decisão |
| :--- | :--- | :--- | :--- |
| **0** | Acessa a plataforma e faz Login / Registro. | Valida credenciais e redireciona para o Dashboard. | — |
| **1** | Clica em **"Nova Correção"**. | Exibe tela com duas abas: "Colar Texto" e "Enviar Arquivo". | — |
| **2a** (Rápido) | Cola o texto digitado e seleciona um **Template de Correção** (ex: ENEM, Fuvest). | Salva o Essay com `status='pending_correction'`. | **Pula revisão**. Vai direto para a correção. |
| **2b** (Scan) | Anexa um arquivo (PDF/JPG/PNG) e seleciona um Template. | Chama a DeepSeek Vision (OCR). Salva o Essay com `status='pending_review'`. | **Redireciona para revisão** (`/review/{id}`). |
| **3** (Scan) | Lê a transcrição, corrige erros de OCR no `<textarea>` e clica em **"Confirmar e Corrigir"**. | Atualiza o texto, muda status para `'pending_correction'`. | — |
| **4** | Aguarda o processamento (15 a 40 segundos). | **Corretor A (Rigoroso)** e **Corretor B (Progressista)** são chamados em paralelo. | Se divergência > 100, chama **Corretor C (Equilibrado)**. |
| **5** | Visualiza o resultado na tela de resultado. | Mostra notas e justificativas para cada competência do template selecionado, lado a lado (A e B). | Se houver C, exibe banner de desempate e a nota oficial (média dos mais próximos). |
| **6** | Acessa o Dashboard para ver histórico e evolução. | Lista todas as redações, com filtros e gráficos de evolução por competência. | — |

---

## 4. Requisitos Funcionais (RF)

| ID | Categoria | Descrição |
| :--- | :--- | :--- |
| **RF01** | Autenticação | Sistema deve permitir cadastro e login com e-mail/senha, gerenciando sessões via cookies seguros. |
| **RF02** | Upload Dual | O sistema deve aceitar redações por *upload de arquivo* (PDF, JPG, PNG) ou *digitação/cola* (texto puro). |
| **RF03** | OCR Inteligente | Para arquivos, o sistema deve usar DeepSeek Vision (via modelo `deepseek-v4-flash`) para transcrever a imagem, mas **obrigatoriamente** passar por uma tela de revisão humana antes da correção. |
| **RF04** | Seleção de Template | No upload, o professor deve selecionar um **Template de Correção** dentre os disponíveis (globais ou criados por ele). |
| **RF05** | Correção Dual com Personas | O sistema deve disparar 2 chamadas simultâneas à DeepSeek (`deepseek-v4-flash`) com System Prompts fixos (Corretor A - Rigoroso; Corretor B - Progressista), mas com **User Prompts dinâmicos** baseados nas competências do template selecionado. |
| **RF06** | Regra do Terceiro Corretor | Se a diferença entre as notas totais de A e B for **> 100 pontos**, o sistema deve chamar um terceiro corretor (C - Equilibrado) e calcular a nota final como a média dos dois corretores mais próximos (descartando o mais distante). |
| **RF07** | Feedback Estruturado | A IA deve retornar notas e justificativas para **cada competência** do template. O sistema deve armazenar esses dados em JSON estruturado (`scores_json`) e também em campos fixos (`c1..c5`) para compatibilidade com dados legados. |
| **RF08** | CRUD de Competências | O professor deve poder **Criar, Listar, Editar e Excluir** competências personalizadas (nome, descrição, pontuação máxima). Competências padrão do sistema (ENEM) são imutáveis (`is_default=True`). |
| **RF09** | CRUD de Templates | O professor deve poder **Criar, Listar, Editar e Excluir** templates de correção, associando um conjunto de competências a um nome/descrição. O template padrão "ENEM Oficial" é imutável. |
| **RF10** | Dashboard de Histórico | O professor deve visualizar todas as redações enviadas, com data, template utilizado, nota final, notas de A e B, e status (Concluído / Falha / Pendente). |
| **RF11** | Estatísticas de Evolução | O sistema deve gerar gráficos (Chart.js) mostrando a evolução da média de notas por competência ao longo do tempo (para o professor ou aluno). |
| **RF12** | Tolerância a Falhas | Se a API da DeepSeek falhar, a redação deve ficar com status `'failed'` e exibir um botão "Tentar Novamente" no Dashboard para re-disparar a correção. |

---

## 5. Requisitos Não Funcionais (RNF)

| ID | Categoria | Descrição |
| :--- | :--- | :--- |
| **RNF01** | Performance | A correção completa (2 IAs) não deve exceder **45 segundos**. Usar `asyncio.gather` para paralelizar as chamadas à API. |
| **RNF02** | Segurança | Chaves da API e `SECRET_KEY` em variáveis de ambiente (`.env`). Senhas hasheadas com `bcrypt`. Sessões gerenciadas com `SessionMiddleware`. |
| **RNF03** | Usabilidade | Front-end responsivo com **Bootstrap 5**, funcionando bem em desktops, tablets e smartphones (professores corrigem em qualquer lugar). |
| **RNF04** | Disponibilidade | O sistema deve tratar falhas da API DeepSeek com mensagens amigáveis e logs estruturados (`logging`). |
| **RNF05** | Extensibilidade | O modelo de dados deve permitir a adição de novas competências sem alterar a estrutura do banco (uso de `scores_json`). |
| **RNF06** | Migração | A migração do sistema legado (com colunas fixas `c1..c5`) para o novo modelo (`scores_json`) deve ser suave, preservando os dados existentes. |

---

## 6. Stack Tecnológica

| Camada | Tecnologia | Justificativa |
| :--- | :--- | :--- |
| **Backend** | **FastAPI** | Alto desempenho, assíncrono nativo, documentação automática (Swagger), fácil integração com Jinja2 e SQLAlchemy. |
| **Banco de Dados** | **SQLite** (dev) / **PostgreSQL** (prod) | SQLite para MVP simples; suporte a `aiosqlite` para operações assíncronas. |
| **ORM** | **SQLAlchemy 2.0 (Async)** | AsyncSession para não bloquear o event loop durante as operações de banco. |
| **Frontend** | **Jinja2 + Bootstrap 5** | Renderização server-side rápida; dispensa framework JS complexo para o MVP. |
| **API de IA** | **DeepSeek v4-flash** | Custo-benefício excelente; suporte nativo a `json_object`; 1M de contexto; alta concorrência. |
| **OCR** | **DeepSeek Vision** (via `deepseek-v4-flash`) | Excelente reconhecimento de texto em imagens e scans de baixa qualidade. |
| **Processamento de Imagem** | **Pillow + pdf2image** | Conversão de PDFs scaneados para imagens. |
| **Autenticação** | **bcrypt + Starlette Sessions** | Seguro e compatível com o ecossistema FastAPI. |

---

## 7. Modelo de Dados (Esquema Lógico)

### 7.1 Tabelas Principais

| Tabela | Descrição | Campos Relevantes |
| :--- | :--- | :--- |
| **users** | Professores/alunos | `id`, `username`, `email`, `password_hash`, `default_template_id`, `created_at` |
| **competences** | Competências (globais ou personalizadas) | `id`, `name`, `description`, `max_score`, `is_default`, `created_by`, `created_at` |
| **correction_templates** | Templates de correção | `id`, `name`, `description`, `is_default`, `created_by`, `created_at` |
| **template_competences** | Associação N:N | `template_id`, `competence_id` |
| **essays** | Redações enviadas | `id`, `user_id`, `template_id`, `source_type`, `raw_text`, `status`, `final_score`, `created_at` |
| **corrections** | Correções realizadas | `id`, `essay_id`, `corrector_type` (A/B/C), `total_score`, **`scores_json`** (campo JSON com estrutura dinâmica), `created_at` |

### 7.2 Estrutura do `scores_json`

```json
{
  "comp_1": { "nota": 160, "justificativa": "Domínio da norma padrão..." },
  "comp_2": { "nota": 180, "justificativa": "Ótimo repertório..." },
  "comp_3": { "nota": 120, "justificativa": "Coesão prejudicada..." },
  "total": 460
}
```

> **Nota:** As chaves `comp_1`, `comp_2` correspondem à ordem das competências no template. O nome/descrição das competências ficam no banco (tabela `competences`), mas recomenda-se salvar uma cópia do nome no JSON para exibição rápida na página de resultado (evita consultas extras).

---

## 8. Lógica de Correção (Algoritmo de Decisão)

1. **Entrada:** Texto da redação + `template_id`.
2. **Busca Competências:** Obtém a lista de competências associadas ao template.
3. **Montagem do Prompt:** Constrói o `user_prompt` dinamicamente:
   ```
   Corrija a redação de acordo com as competências:
   1. [nome]: [descrição] (0 a [max_score])
   2. ...
   Retorne JSON: {"comp_1": {"nota": int, "justificativa": "..."}, ..., "total": int}
   ```
4. **Execução Paralela (A e B):**
   - **A (Rigoroso):** System Prompt focado em Gramática e Coesão; `temperature=0.3`.
   - **B (Progressista):** System Prompt focado em Tema, Repertório e Intervenção; `temperature=0.8`.
5. **Cálculo da Divergência:**
   - `diff = abs(total_A - total_B)`.
   - Se `diff > 100` → Chama **Corretor C** (Equilibrado; `temperature=0.5`).
6. **Nota Final (Regra Oficial):**
   - Se `diff ≤ 100`: `nota_final = (total_A + total_B) / 2`.
   - Se `diff > 100`: Identifica os dois corretores com as notas mais próximas entre si (pares A-B, A-C, B-C) e calcula a média aritmética simples entre eles. Exemplo: `(A + C) / 2`.
7. **Persistência:** Salva as três correções (se houver C) com `scores_json` e atualiza o Essay com `status='completed'` e `final_score`.

---

## 9. Especificação da API DeepSeek (Modelo v4-flash)

| Parâmetro | Valor | Detalhe |
| :--- | :--- | :--- |
| **Modelo** | `deepseek-v4-flash` | Modelo otimizado para custo/velocidade, com suporte a `response_format`. |
| **Endpoint** | `https://api.deepseek.com/chat/completions` | Padrão OpenAI-compatible. |
| **System Prompt** | Fixo por corretor (A/B/C) | Não menciona competências específicas; mantém-se genérico para flexibilidade. |
| **User Prompt** | Dinâmico | Gerado a partir das competências do template. |
| **Temperatura** | A: 0.3 / B: 0.8 / C: 0.5 | Controla criatividade/rigor. |
| **response_format** | `{"type": "json_object"}` | Força a saída em JSON válido, eliminando necessidade de parse manual complexo. |
| **max_tokens** | 4096 | Suficiente para justificativas detalhadas para até 10 competências. |
| **Timeout** | 60 segundos | Protege contra travamentos. |

---

## 10. Cronograma e Entregáveis (Sugestão para Desenvolvimento)

| Fase | Atividade | Duração Estimada |
| :--- | :--- | :--- |
| **1** | Setup, Autenticação e Modelos Base | 2 dias |
| **2** | Upload, OCR e Revisão Humana | 2 dias |
| **3** | Correção Dual (A/B/C) com Prompt Fixo | 3 dias |
| **4** | Dashboard e Página de Resultados | 2 dias |
| **5** | **CRUD de Competências e Templates** | 3 dias |
| **6** | Integração do CRUD com o Serviço de Correção | 2 dias |
| **7** | Estatísticas, Tratamento de Erros e Polimento | 2 dias |
| **8** | Testes End-to-End e Deploy (Railway / Vercel / Self-hosted) | 2 dias |
| **Total** | — | **18 dias úteis** |

---

## 11. Próximos Passos (Roadmap Pós-MVP)

| Feature | Descrição |
| :--- | :--- |
| **Banco de Dados de Redações** | Permitir que o professor salve redações modelos (nota mil) para comparar com as do aluno. |
| **Feedback por Áudio** | Gerar um áudio (TTS) com o feedback principal para o aluno ouvir. |
| **Plano de Assinatura** | Limitar número de correções gratuitas; planos pagos por correção ou mensalidade. |
| **Modo Aluno** | Criar login para alunos, onde eles veem apenas suas próprias redações e feedbacks, sem acesso ao dashboard do professor. |
| **Integração com Google Classroom** | Sincronizar turmas e tarefas. |

---

## 12. Glossário

| Termo | Definição |
| :--- | :--- |
| **Competência** | Critério de avaliação (ex: Gramática, Tema). Cada uma tem uma nota máxima (geralmente 200) e uma descrição. |
| **Template** | Agrupamento de competências que define o "formato" de uma correção (ex: "ENEM 2025"). |
| **Corretor A/B/C** | Personas da IA. A = Rigoroso (foco gramatical); B = Progressista (foco argumentativo); C = Equilibrado (desempate). |
| **scores_json** | Campo JSON que armazena as notas e justificativas de todas as competências de uma correção. |
