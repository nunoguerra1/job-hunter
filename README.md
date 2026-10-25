# job-hunter

Radar de vagas com IA. Ele coleta vagas de estágio, trainee e júnior, dá uma nota de compatibilidade
com o meu perfil, prepara o texto da candidatura e o currículo em PDF de cada vaga, registra tudo
numa planilha e me ajuda a preencher formulários.

**Regra de ouro:** nenhuma candidatura é enviada sem eu aprovar, e o clique final de "Enviar" é
sempre meu. O sistema prepara, sugere e organiza. Quem decide e envia sou eu.

## Sumário

1. [O que o sistema faz e o que não faz](#1-o-que-o-sistema-faz-e-o-que-não-faz)
2. [Visão geral do fluxo](#2-visão-geral-do-fluxo)
3. [Instalação e configuração (feito uma vez)](#3-instalação-e-configuração-feito-uma-vez)
4. [Rotina diária, passo a passo](#4-rotina-diária-passo-a-passo)
5. [Rotina semanal e ocasional](#5-rotina-semanal-e-ocasional)
6. [A planilha](#6-a-planilha)
7. [Status de uma candidatura](#7-status-de-uma-candidatura)
8. [Referência de comandos](#8-referência-de-comandos)
9. [Como personalizar](#9-como-personalizar)
10. [Limites e cotas](#10-limites-e-cotas)
11. [Segurança e privacidade](#11-segurança-e-privacidade)
12. [Solução de problemas](#12-solução-de-problemas)
13. [Limitações conhecidas](#13-limitações-conhecidas)
14. [Estrutura de pastas](#14-estrutura-de-pastas)
15. [Desenvolvimento](#15-desenvolvimento)

---

## 1. O que o sistema faz e o que não faz

**Faz:**

- Coleta vagas da Gupy, Adzuna, Remotive e, se configurados, de quadros Greenhouse e Lever.
- Descarta o que não serve: prazo vencido, vaga exclusiva para PcD, nível acima do meu, suporte de
  TI, fora de TI.
- Dá nota de 0 a 100 de compatibilidade (IA) e estima o custo de vida da cidade da vaga.
- Para as melhores vagas, escreve o "por que você quer trabalhar conosco?", a pretensão salarial
  e gera um currículo em PDF de 1 página adaptado à vaga.
- Me manda cada candidatura no Telegram para eu aprovar, editar ou descartar.
- Preenche as perguntas de formulário da Gupy que eu autorizei e deixa o resto em vermelho.
- Lê os cabeçalhos dos meus e-mails (reprovação, avanço de etapa, convite para teste) e atualiza a
  planilha.

**Não faz:**

- Não clica em "Salvar e continuar" nem em "Enviar candidatura".
- Não inventa respostas. Assuntos sensíveis (salário, mudança de cidade, CNH, PcD, documentos,
  diversidade) ficam sempre para mim, a menos que eu tenha criado uma regra com `force: true`.
- Não sabe se a plataforma aceitou a candidatura. Ele só registra o que eu informo. A prova de
  verdade é o e-mail de confirmação da empresa.
- Não lê o corpo dos e-mails (só cabeçalhos e um trecho curto dos que são ambíguos).

---

## 2. Visão geral do fluxo

```
 FONTES                 PROCESSAMENTO                 VOCÊ                    RESULTADO
 -------                -------------                 ----                    ---------
 Gupy                   1. pré-filtro (regras)        Telegram:               Planilha Google
 Adzuna          --->   2. nota de match (IA)  --->   Aprovar / Editar /  ---> (abas "Vagas" e
 Remotive               3. texto + PDF por vaga       Descartar                "Candidaturas")
 Greenhouse / Lever     4. planilha                   Enviar: clique seu
 Gmail (andamento)                                    Informar "s" ao enviar
```

Em termos de comandos, o dia tem **três momentos**:

| Momento | Comando | O que acontece |
|---|---|---|
| Preparar | `python -m jobhunter.daily` | Coleta, e-mails, notas, candidaturas, planilha, envia ao Telegram |
| Decidir | `python -m jobhunter.bot` | Fica ouvindo os seus cliques (Aprovar, Editar, Descartar) |
| Enviar | `python -m jobhunter.apply fill <id>` | Abre a vaga, preenche o que pode, você envia |

---

## 3. Instalação e configuração (feito uma vez)

### 3.1 Requisitos

- Windows (os comandos abaixo são do PowerShell), Python 3.11 ou mais novo, Git.
- Contas gratuitas: Google (Gemini, Sheets, Gmail), Telegram e Adzuna (opcional).

### 3.2 Instalar o projeto

```powershell
git clone git@github.com:SEU_USUARIO/job-hunter.git
cd job-hunter
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m playwright install chromium
```

- O `(.venv)` no começo da linha do terminal mostra que o ambiente está ativo. **Em todo terminal
  novo** é preciso ir até a pasta do projeto e rodar `.venv\Scripts\activate` de novo.
- Se o PowerShell bloquear o `activate`, rode uma vez:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- O último comando baixa o navegador (Chromium) que o sistema usa para PDF e formulários.

### 3.3 O arquivo `.env`

Copie `.env.example` para `.env` e preencha. Este arquivo **nunca** vai para o Git.

```powershell
Copy-Item .env.example .env
```

| Variável | Para que serve | Onde conseguir |
|---|---|---|
| `GEMINI_API_KEY` | IA que dá a nota e escreve os textos | aistudio.google.com, "Get API key" |
| `GEMINI_MODELS` | Modelos separados por vírgula; o 1º é o preferido e os outros são reserva | ai.dev/rate-limit mostra os nomes e as cotas |
| `GOOGLE_CREDENTIALS_PATH` | Chave da conta de serviço (planilha) | passo 3.4 |
| `GOOGLE_SHEET_ID` | Qual planilha usar | trecho da URL entre `/d/` e `/edit` |
| `TELEGRAM_BOT_TOKEN` | Controle do seu bot | @BotFather, comando `/newbot` |
| `TELEGRAM_CHAT_ID` | Só este chat pode usar o bot | passo 3.6 |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Fonte de vagas Adzuna (opcional) | developer.adzuna.com |

### 3.4 Planilha (Google Sheets)

1. No Google Cloud Console, use um projeto e ative a **Google Sheets API**.
2. Em **IAM e administrador > Contas de serviço**, crie uma conta (ex.: `job-hunter-bot`). Não
   precisa dar papel de acesso.
3. Na conta, aba **Chaves > Adicionar chave > Criar nova chave > JSON**.
4. Salve o arquivo baixado como `credentials/service_account.json`.
5. Crie uma planilha no Google Sheets, clique em **Compartilhar** e dê permissão de **Editor** ao
   e-mail que está em `client_email` dentro do JSON.
6. Copie o ID da planilha para `GOOGLE_SHEET_ID` e o caminho do JSON para `GOOGLE_CREDENTIALS_PATH`
   (`credentials/service_account.json`).

### 3.5 E-mails (Gmail, somente leitura)

1. No mesmo projeto, ative a **Gmail API**.
2. Configure a tela de consentimento OAuth (público externo), adicione o seu Gmail como usuário de
   teste e o escopo `https://www.googleapis.com/auth/gmail.readonly`.
3. Crie um **ID do cliente OAuth** do tipo "App para computador", baixe o JSON e salve como
   `credentials/gmail_oauth_client.json`.
4. Na primeira vez que rodar `python -m jobhunter.mail sync`, o navegador abre pedindo autorização.
   Aceite (se aparecer o aviso de app não verificado, continue: o app é seu).

O token fica em `credentials/gmail_token.json`. Em modo de teste, o Google costuma expirar a
autorização a cada 7 dias, e o navegador abre de novo para você autorizar.

### 3.6 Telegram

1. No Telegram, abra o **@BotFather**, envie `/newbot`, escolha nome e usuário (terminando em
   `bot`) e copie o token para `TELEGRAM_BOT_TOKEN`.
2. Abra o chat com o seu bot e envie `/start` (o bot só consegue escrever depois que você fala).
3. Descubra o seu chat id: `python -m jobhunter.telegram`. Copie o número para `TELEGRAM_CHAT_ID`.

### 3.6.1 Adzuna (opcional)

Crie conta em developer.adzuna.com e coloque `ADZUNA_APP_ID` e `ADZUNA_APP_KEY` no `.env`. As buscas
ficam em `config/sources.yaml`.

### 3.7 Arquivos de perfil (`profile/`)

Os arquivos reais ficam fora do Git. Os `*.example.yaml` mostram o formato.

```powershell
Copy-Item profile\profile.example.yaml profile\profile.yaml
Copy-Item profile\story_bank.example.yaml profile\story_bank.yaml
Copy-Item profile\cv_base.example.yaml profile\cv_base.yaml
Copy-Item profile\answers.example.yaml profile\answers.yaml
```

| Arquivo | O que colocar | Atenção |
|---|---|---|
| `profile.yaml` | curso, data de formatura, cidade, habilidades, idiomas, experiência, projetos, motivação, piso salarial (`min_salary` para estágio, `min_salary_clt` para CLT) | A IA só enxerga o que está aqui. Se uma habilidade não está na lista, ela é tratada como lacuna |
| `story_bank.yaml` | histórias no formato Situação, Tarefa, Ação, Resultado e bullets do currículo | O sistema recusa rodar enquanto houver o texto `PREENCHER`. Só fatos verdadeiros: a IA usa isso para escrever o "por que nós?" |
| `cv_base.yaml` | currículo completo (contatos, experiência, projetos, formação, conhecimentos) | Os 4 contatos começam como `PREENCHER` |
| `answers.yaml` | regras de resposta automática de formulário (ver seção 9) | Só automatize o que for verdade |

### 3.8 Configurações (`config/`)

- `config/cost_of_living.yaml`: custo mensal estimado por cidade (aluguel, comida, transporte,
  outros). São estimativas: ajuste com a sua realidade.
- `config/sources.yaml`: buscas da Adzuna e quadros Greenhouse/Lever (seção 9).

### 3.9 Login na Gupy (uma vez)

```powershell
python -m jobhunter.apply login
```

O Chromium abre na Gupy. Faça o login normalmente (a senha é digitada por você no navegador e
**não passa pelo código**) e volte ao terminal para apertar Enter. A sessão fica salva em
`data/browser_profile` (pasta fora do Git, com cookies: não compartilhe).

### 3.10 Primeira execução, passo a passo

Na primeira vez, rode as etapas separadas para ver cada erro isolado:

```powershell
python -m jobhunter                 # coleta vagas e mostra o resumo do pré-filtro
python -m jobhunter.mail sync       # lê os e-mails (abre o navegador na 1ª vez)
python -m jobhunter.score 20        # dá nota a até 20 vagas
python -m jobhunter.sync            # cria e preenche a planilha
python -m jobhunter.prepare 3       # prepara as 3 melhores candidaturas
python -m jobhunter.bot --notify-only   # envia ao Telegram
```

Depois disso, o dia a dia é só a seção 4.

---

## 4. Rotina diária, passo a passo

Você vai usar **dois terminais** (duas janelas ou duas abas do terminal do VS Code). Em cada um:

```powershell
cd D:\caminho\para\job-hunter
.venv\Scripts\activate
```

### Passo 1: preparar o dia (Terminal 1)

```powershell
python -m jobhunter.daily
```

Leva alguns minutos. Ele roda 6 etapas em sequência e imprime um bloco para cada uma:

1. **Coleta de vagas:** mostra quantas vagas vieram de cada fonte e quantas são novas. Depois mostra
   quantas passaram no pré-filtro e por que as outras foram descartadas.
2. **E-mails:** classifica os e-mails de candidatura (recebida, avançou, reprovada...). Lista
   também os que ele não conseguiu decidir sozinho, na forma `abra e leia: ...`.
3. **Nota de match:** dá nota a até 40 vagas novas, em lotes de 5, e mostra o ranking.
4. **Candidaturas:** prepara as 3 melhores (nota 70 ou mais, curso compatível, sem "banco de
   talentos") e cria a pasta `output/<vaga>/` com o texto e o PDF.
5. **Planilha:** atualiza as abas "Vagas" e "Candidaturas".
6. **Telegram:** envia as candidaturas novas para revisão (os botões só funcionam no Passo 3).

No fim ele imprime `Resumo: tudo certo.` ou `falhou em ...`. **Um passo que falha não derruba os
seguintes.** Erros temporários de IA (503) aparecem como `ERRO no lote` e são tentados de novo na
próxima rodada.

> Dica: para pular etapas, use `--skip=`. Exemplo: `python -m jobhunter.daily --skip=mail,prepare`.

### Passo 2: ler o que o sistema não decidiu sozinho

Procure no resultado as linhas `abra e leia: ...`. São e-mails ambíguos (por exemplo "Atualização
sobre o processo seletivo", que pode ser aprovação ou reprovação). **Abra cada um no Gmail**,
principalmente as `mensagem do recrutador`, que costumam pedir resposta e podem ter prazo.

### Passo 3: decidir no Telegram (Terminal 1)

Ainda no Terminal 1, ou numa janela só para isso:

```powershell
python -m jobhunter.bot
```

Aparece `Bot ouvindo o Telegram (Ctrl+C para parar)...`. **Deixe esse terminal aberto**: o bot só
responde enquanto ele estiver rodando. Agora vá ao Telegram, no chat com o seu bot. Para cada
candidatura você recebe:

1. o **PDF do currículo** adaptado à vaga;
2. uma **mensagem** com vaga, empresa, local, nota, resposta de salário, link e o texto "por que
   você quer trabalhar conosco?", com três botões.

O que cada botão faz:

- **Aprovar:** a candidatura vai para a fila de envio (`apply list`).
- **Editar:** o bot pede o novo texto. Envie, **numa única mensagem**, o "por que nós?" que você
  quer. Ele substitui o rascunho e reenvia para você decidir de novo. Para desistir, envie
  `/cancelar`.
- **Descartar:** a candidatura sai da fila.

Cada clique aparece no terminal como `recebido: clique approve:gupy:12345`.

Cuidados:

- Leia o texto antes de aprovar. Ele é um rascunho: se tiver algo que você não sustentaria numa
  entrevista, use **Editar**.
- No Windows, clicar dentro da janela do PowerShell pausa o programa. Se o bot parar de responder,
  aperte Enter nessa janela.
- Só pode existir **um** bot rodando. Se aparecer erro 409, há outra instância aberta.
- Se você ainda não rodou o bot, não perde nada: o Telegram guarda os cliques por até 24 horas.

Quando terminar de decidir, volte ao terminal e aperte **Ctrl+C**. O bot encerra.

### Passo 4: enviar as aprovadas (Terminal 2)

Abra o segundo terminal (com o ambiente ativo) e liste o que está aprovado:

```powershell
python -m jobhunter.apply list
```

Cada linha mostra o **id** da vaga (ex.: `gupy:12542291`), o prazo e o link. O caminho depende de
onde a vaga está.

#### 4A. Vaga da Gupy (id começa com `gupy:`)

```powershell
python -m jobhunter.apply fill gupy:12542291
```

1. O Chromium abre a vaga. Se ela já encerrou, o programa avisa, marca como `closed` e para.
2. Clique em **Candidatar-se** e avance até a tela de **perguntas** (os dados pessoais costumam
   vir pré-preenchidos pelo seu perfil na Gupy).
3. **Espere a tela terminar de carregar.** Depois volte ao terminal e aperte **Enter** (linha
   vazia) no prompt `>`.
4. O programa responde as perguntas que estão no seu `answers.yaml` e imprime o que fez:
   `[ok]` para o que preencheu e `[ ! ]` para o que ficou com você. Na página, o que ficou para você
   fica com **contorno vermelho**, e aparece um aviso no canto da tela.
5. **Responda você mesmo as perguntas em vermelho** e revise as que ele preencheu.
6. Clique **você** em "Salvar e continuar".
7. Repita os passos 3 a 6 em cada etapa de perguntas.
8. Na tela final, revise e clique **você** em **Enviar candidatura**. A Gupy avisa que as respostas
   não poderão ser editadas depois, então confira tudo antes.
9. Volte ao terminal e digite **`s`** e Enter para marcar como enviada. Se você desistiu, digite
   **`q`**: ele sai sem marcar nada e imprime o comando para marcar depois.

Comandos do prompt `>`:

| Digite | Efeito |
|---|---|
| Enter (vazio) | Preenche a etapa atual (só em páginas da Gupy) |
| `s` | Já me candidatei: marca como enviada e sai |
| `q` | Sai sem marcar nada |

#### 4B. Vaga de outra fonte (Adzuna, Greenhouse, Lever, Remotive)

O preenchimento automático só conhece o formulário da Gupy. Faça assim:

1. Abra o link que o `apply list` mostrou.
2. Use os arquivos da pasta `output/<id_da_vaga>/`: `candidatura.md` (o texto do "por que nós?" e a
   pretensão) e `curriculo.pdf` (para anexar). O nome da pasta troca `:` por `_`
   (ex.: `output/adzuna_5937187219/`).
3. Envie a candidatura pelo site.
4. Marque como enviada:

```powershell
python -m jobhunter.apply mark adzuna:5937187219
```

### Passo 5: conferir se a candidatura foi computada

O sistema só sabe o que você informa. Para conferir de verdade:

```powershell
python -m jobhunter.apply status
```

mostra quantas candidaturas estão em cada status e lista as **Enviadas** e as **Aprovadas ainda
não enviadas**. A confirmação real é o **e-mail da empresa** ("Inscrição recebida", "Candidatura
recebida com sucesso"), que costuma chegar em minutos. Para trazê-lo para a planilha:

Para trazer a **etapa atual** (ex.: `1/7`) direto da sua conta da Gupy, rode (o Chromium abre,
já logado, e lê a tela "Minhas candidaturas"; ele só lê e não clica em nada que mude candidatura):

    python -m jobhunter.progress

Ele também marca como enviadas as vagas que aparecem na sua lista da Gupy e mostra as candidaturas
que você fez fora do sistema como "sem vaga ligada".

```powershell
python -m jobhunter.mail sync
python -m jobhunter.sync
```

Se uma vaga que você enviou ainda aparece como "aprovada" no `status`, marque com
`python -m jobhunter.apply mark <id>`.

### Resumo da rotina em 5 linhas

```
Terminal 1:  python -m jobhunter.daily          # prepara (alguns minutos)
             (ler os e-mails marcados "abra e leia")
Terminal 1:  python -m jobhunter.bot            # clicar Aprovar / Editar / Descartar no Telegram
             Ctrl+C quando terminar
Terminal 2:  python -m jobhunter.apply list     # ver as aprovadas
             python -m jobhunter.apply fill <id>   # Gupy: preencher, revisar, enviar, digitar "s"
             python -m jobhunter.apply mark <id>   # outras fontes: depois de enviar
             python -m jobhunter.apply status   # conferir
```

Ritmo recomendado: poucas candidaturas por dia, todas revisadas por você. Candidatura em massa
piora a qualidade e aumenta o risco de a plataforma estranhar o uso.

---

## 5. Rotina semanal e ocasional

| Quando | Comando | Para quê |
|---|---|---|
| Quando fizer candidaturas | `python -m jobhunter.mail sync` e `python -m jobhunter.sync` | Trazer reprovações, avanços e convites para a planilha |
| Toda semana | `python -m jobhunter.followups` | Lista candidaturas enviadas há 10 dias ou mais sem nenhum e-mail de andamento |
| Antes de enviar uma vaga antiga | `python -m jobhunter.apply check` | Marca como `closed` as vagas que encerraram na página |
| Depois de usar o `fill` em várias vagas | `python -m jobhunter.apply gaps` | Mostra as perguntas de formulário que ainda não têm regra, as mais frequentes primeiro |
| Quando mudar algo na vida acadêmica | editar `expected_graduation` em `profile/profile.yaml` | Os textos e as notas passam a usar a data nova |
| Ao querer mais vagas home office | `python -m jobhunter.boards find <link de uma vaga>` | Descobre o código do quadro Greenhouse ou Lever de uma empresa |
| Se a planilha ficar bagunçada | `python -m jobhunter.sync --rebuild` | Reconstrói a planilha (**apaga edições manuais** de Status e Etapas) |
| Depois de se candidatar na Gupy | `python -m jobhunter.progress` e `python -m jobhunter.sync` | Preenche a coluna Etapas e a aba Gupy |

### Rodar o `daily` sozinho (opcional)

Crie `daily.bat` **fora do repositório** (ele tem o seu caminho):

```bat
@echo off
cd /d D:\caminho\para\job-hunter
.venv\Scripts\python -m jobhunter.daily --skip=mail >> data\daily.log 2>&1
```

No **Agendador de Tarefas**: Criar Tarefa Básica, diária, iniciar um programa, escolher o `.bat`. Em
Propriedades > Configurações, marque "executar assim que possível após uma inicialização perdida".
Use `--skip=mail` no agendado, porque se a autorização do Gmail expirar, o navegador abriria e o
programa ficaria esperando você. O bot do Telegram só **envia** as candidaturas nesse modo: os
botões funcionam quando você rodar `python -m jobhunter.bot`.

---

## 6. A planilha

Duas abas.

### Aba "Vagas"

Uma linha por vaga com nota 60 ou mais e curso compatível, ordenada por nota.

| Coluna | Significado |
|---|---|
| Título, Empresa, Tipo de cargo | Dados da vaga (estágio, trainee ou júnior) |
| Salário, Benefícios | Só aparecem se a empresa escreveu na descrição. Senão: "não informado" |
| Modalidade, Local | home office, presencial ou híbrida |
| Custo de vida/mês | Estimativa da cidade da vaga (do `cost_of_living.yaml`). Com `~` quando a cidade não está na tabela. Em vaga home office, usa a sua cidade |
| Sobra estimada | Salário menos custo de vida. Sem salário: "sem salário: precisa ~R$ X" |
| Nota | Compatibilidade de 0 a 100 (ver abaixo) |
| Resumo da IA | Em 1 ou 2 frases, o motivo da nota |
| Publicada, Prazo | Datas da vaga |
| Etapas | Etapa atual e total como a Gupy mostra (ex.: 1/7), vinda de python -m jobhunter.progress. Vagas de outras fontes ficam ?/? |
| Status | Ver seção 7 |
| Link, ID | Link da vaga e o id que você usa nos comandos |

**Como ler a nota:** 80 ou mais é candidatura forte; 60 a 79 vale tentar; abaixo de 60 é fraca. A
nota varia uns 5 pontos entre execuções, então use faixas, não o número exato. Nota alta não
significa vaga boa: vaga com descrição curta tende a receber nota alta porque nada conflita com o
perfil. Leia sempre o resumo.

Editar à mão é seguro: o sistema só **acrescenta** vagas novas e só troca o Status quando o valor
atual foi escrito por ele mesmo. O que você anotar (Entrevista, Teste, etc.) é preservado. A única
exceção é o `--rebuild`.

### Aba "Candidaturas"

Uma linha por e-mail de candidatura (inclusive de vagas que você enviou fora do sistema): data,
situação, empresa ou remetente (estimado, pode errar), assunto e, quando a empresa bate com **uma
única** vaga da aba "Vagas", qual é ela.

### Aba "Gupy"

Todas as candidaturas da sua conta na Gupy (inclusive as feitas fora do sistema), com a etapa,
a aba da Gupy (em andamento, banco de talentos ou finalizadas) e, quando existe, a vaga ligada.
É gerada do zero a cada `sync`: não edite nela.

---

## 7. Status de uma candidatura

**No banco** (o que `apply status` mostra):

| Status | Significado |
|---|---|
| `awaiting` | Enviada ao Telegram, aguardando a sua decisão |
| `approved` | Você aprovou, ainda não enviou |
| `discarded` | Você descartou |
| `applied` | Você informou que enviou |
| `expired` | O prazo passou antes de você decidir |
| `closed` | A página da vaga mostrou "inscrições encerradas" |

**Na planilha** (coluna Status):

| Valor | Origem |
|---|---|
| Nova, Banco de talentos | Quando a vaga entra |
| Em revisão, Aprovada, Descartada, Enviada, Encerrada | Das suas decisões e do prazo |
| Recebida pela empresa, Avançou de etapa, Ação necessária, Mensagem do recrutador, Reprovada | Dos e-mails, quando o e-mail se liga a uma vaga sem ambiguidade |

"Banco de talentos" é cadastro de currículo, geralmente sem vaga aberta de verdade, por isso o
sistema não prepara candidatura para ele automaticamente.

---

## 8. Referência de comandos

Todos começam com `python -m jobhunter`.

| Comando | O que faz |
|---|---|
| `.daily [--skip=a,b]` | Rotina completa. Etapas que podem ser puladas: `collect`, `mail`, `score`, `prepare`, `sync`, `telegram` |
| (sem sufixo) | Só coleta vagas e mostra o resumo do pré-filtro |
| `.score [N]` | Dá nota a até N vagas novas (padrão 40), em lotes de 5. Para sozinho quando a cota acaba |
| `.prepare [N]` | Prepara as N melhores candidaturas (padrão 3, nota 70 ou mais) |
| `.prepare <id>` | Prepara uma vaga específica (ex.: `gupy:12345`). Gasta 1 requisição de IA |
| `.make_cv [id]` | Gera os PDFs que faltam (ou refaz o de uma vaga) |
| `.sync [nota] [--rebuild]` | Atualiza a planilha. Nota mínima padrão 60 |
| `.mail sync [qtd]` | Guarda os e-mails de candidatura no banco |
| `.mail inspect [qtd] [--snippets] [--all]` | Só mostra a classificação dos e-mails, sem gravar |
| `.bot [--notify-only] [--resend <id>]` | Bot do Telegram. `--notify-only` só envia. `--resend` reenvia uma candidatura já preparada |
| `.telegram` | Descobre o seu chat id |
| `.apply login` | Login na Gupy (uma vez) |
| `.apply list` | Candidaturas aprovadas com prazo e link |
| `.apply fill <id>` | Preenche formulário da Gupy (Enter, `s`, `q`) |
| `.apply mark <id>` | Marca como enviada |
| `.apply status` | Resumo por status e lista de enviadas e aprovadas |
| `.apply check` | Visita as vagas em revisão ou aprovadas e marca as encerradas |
| `.apply inspect <id>` | Captura a estrutura das telas de um formulário (uso técnico, para criar regras) |
| `.apply gaps` | Perguntas de formulário sem regra, por frequência |
| `.followups [dias]` | Candidaturas enviadas há N dias (padrão 10) sem e-mail de andamento |
| `.boards find <link>` | Descobre o código do quadro Greenhouse ou Lever |
| `.boards check <tipo> <código>` | Confirma que o quadro existe e lista algumas vagas |
| `.mail link` | Mostra a qual vaga cada e-mail guardado se liga. Útil quando o Status da planilha não atualiza |
| `.snap` | Captura o texto visível de telas da Gupy (com máscara de dados pessoais), para criar novos recursos |
| `.progress` | Lê "Minhas candidaturas" da Gupy: etapas (n/m), marca enviadas e liga às vagas |
| `.progress link <id da vaga> <id da candidatura>` | Liga à mão uma candidatura a uma vaga |
| `.progress dump` | Salva o texto de cada aba de "Minhas candidaturas" (com máscara de dados pessoais) em `data/pages/` |
| `.progress link - <número da candidatura>` | Desfaz uma ligação errada entre uma candidatura da Gupy e uma vaga |
| `.progress stats` | Resume as candidaturas finalizadas por tipo de contrato e modalidade (reprovada x encerrada) e as em andamento por etapa |

---

## 9. Como personalizar

### `profile/answers.yaml`: respostas automáticas de formulário

```yaml
rules:
  - when: ["escolaridade"]
    choose: ["Ensino superior cursando"]

  - when: ["por que", "trabalhar"]
    text: "{why_us}"
```

- `when`: uma regra vale quando **todas** as expressões aparecem no enunciado da pergunta (sem
  diferenciar maiúscula nem acento).
- `choose`: a(s) opção(ões) a marcar. Tem de existir exatamente nas opções da pergunta, senão o
  campo fica para você.
- `text`: texto livre. Pode usar `{why_us}`, `{salary_answer}` e `{cv_summary}`, que vêm do
  rascunho já aprovado no Telegram.
- `ask: true`: sempre deixa para você.
- `force: true`: obrigatório para automatizar assuntos sensíveis (salário, mudança, CNH, PcD...).
  Use com muito cuidado.

Só crie uma regra para algo que seja **verdade**. Para saber quais perguntas valem uma regra, use
`python -m jobhunter.apply gaps`.

### `config/sources.yaml`: mais fontes de vagas

```yaml
greenhouse:
  - token: codigo-da-empresa
    company: Nome da Empresa
    any_location: true   # empresa brasileira: aceita qualquer cidade
lever: []
adzuna:
  queries: ["estágio desenvolvedor remoto"]
  max_pages: 2
```

Para achar o `token` de uma empresa, abra uma vaga dela e rode
`python -m jobhunter.boards find <link>`. Depois confirme com
`python -m jobhunter.boards check greenhouse <token>`. Só entram vagas de estágio, trainee ou
júnior (pelo título) e, em empresas globais, só as que citam Brasil, LATAM ou "anywhere".

### `config/cost_of_living.yaml`

Custo mensal por cidade. Cidades que não estão na tabela usam um valor médio (marcado com `~` na
planilha). Ajuste os números com a sua realidade.

---

## 10. Limites e cotas

- **IA (Gemini, plano gratuito):** a cota diária é pequena (em testes, 20 requisições por dia por
  modelo; confira em ai.dev/rate-limit). Por isso a nota é dada em lotes de 5 vagas e cada
  candidatura preparada gasta 1 requisição. Rodar o `daily` duas vezes no mesmo dia pode esgotar a
  cota: o programa avisa, para limpo e tenta de novo na próxima rodada. Colocar um segundo modelo em
  `GEMINI_MODELS` dá uma cota extra.
- **Erros 503:** a IA está sobrecarregada. É temporário. O sistema tenta de novo sozinho.
- **Adzuna:** o plano gratuito tem limites não divulgados. Mantenha poucas buscas.
- **Gmail:** só leitura. O Google pode pedir nova autorização a cada 7 dias em modo de teste.

---

## 11. Segurança e privacidade

- **Nunca** coloque no Git, em chat, em issue ou em print: `.env`, `credentials/`, `data/`,
  `output/` e os arquivos reais de `profile/`. Eles já estão no `.gitignore`. Confira com
  `git status` antes de cada commit.
- O JSON da conta de serviço, o token do Telegram, a chave da Adzuna e o token do Gmail dão
  acesso à sua conta. Se algum vazar: apague a chave no Google Cloud e gere outra, use `/revoke` no
  @BotFather ou revogue o acesso em myaccount.google.com/permissions.
- O prompt da IA recebe curso, habilidades, experiência, projetos e resumo, **nunca** seu nome,
  telefone, e-mail, CPF nem endereço. No plano gratuito, o Google pode usar o que é enviado para
  melhorar produtos, então não coloque dados sensíveis no `profile.yaml` nem no `story_bank.yaml`.
- Dos e-mails, o sistema guarda só remetente, assunto, data, uma classificação e a empresa
  estimada. O corpo nunca é gravado.
- O bot do Telegram só responde ao seu `TELEGRAM_CHAT_ID`.
- `data/browser_profile/` guarda cookies de login. Não compartilhe.
- Automatizar plataformas de terceiros pode ir contra os termos de uso delas. Por isso o sistema
  nunca envia sozinho nem roda em massa.

---

## 12. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| O bot não reage aos botões do Telegram | O bot não está rodando; há duas instâncias (erro 409); a janela do PowerShell está pausada | Rode `python -m jobhunter.bot` em um único terminal, sem `--notify-only`, e aperte Enter na janela se ela parecer travada |
| O Telegram não mandou uma candidatura que eu esperava | Ela já tinha sido enviada antes (status `awaiting`) | `python -m jobhunter.bot --resend <id>`. Se você gerou o rascunho de novo com `prepare`, ela volta para a fila sozinha |
| Erro 503 ou 429 da IA | 503: sobrecarga temporária. 429 com "PerDay": cota diária esgotada | Espere ou rode mais tarde. Adicione um segundo modelo em `GEMINI_MODELS` |
| A planilha parece vazia | Os dados estão na aba "Vagas", não na primeira aba | Clique na aba "Vagas" no rodapé |
| Erro 403 na planilha | A planilha não foi compartilhada com o `client_email` | Compartilhe como Editor com o e-mail do JSON |
| `Credenciais não encontradas em ...` | Caminho errado em `GOOGLE_CREDENTIALS_PATH` ou nome do arquivo trocado | Confira a pasta `credentials/` e o `.env` |
| O navegador abre pedindo autorização do Gmail | O token expirou | Aceite de novo. Se for rodada agendada, use `--skip=mail` |
| `[gupy] ERRO` ou 404 na coleta | A Gupy mudou o endereço interno que o sistema usa | Cole o erro completo para ajustar o coletor |
| `Banco de histórias indisponível` ou `Currículo-base indisponível` | Ainda há `PREENCHER` em `story_bank.yaml` ou `cv_base.yaml` | Complete os campos com dados reais |
| `fill` não preenche nada | A página não é da Gupy, ou nenhuma pergunta tem regra | Veja `apply gaps` e crie regras. Em outra fonte, envie à mão e use `apply mark` |
| `ATENÇÃO: 2 páginas` ao gerar o PDF | Conteúdo demais mesmo no layout mais compacto | Encurte bullets em `cv_base.yaml` |
| A vaga "sumiu" do `apply list` | Foi marcada como enviada, ou o prazo venceu | Rode `apply status` |
| `playwright` reclama de navegador não instalado | Chromium não foi baixado | `python -m playwright install chromium` |
| O Status da planilha não mostra o andamento do e-mail | Os e-mails ainda não estão no banco, ou o nome da empresa não bate com uma única vaga | `python -m jobhunter.mail sync`, depois `python -m jobhunter.mail link` para ver cada ligação, e `python -m jobhunter.sync` |

---

## 13. Limitações conhecidas

- **Etapas (ex.: 2/4):** a coluna existe, mas fica `?/?`. Os e-mails dizem a **situação** (recebida,
  avançou, reprovada), mas não o total de etapas.
- **Preenchimento automático só na Gupy**, e só das perguntas. O upload do PDF ainda é manual.
- **Home office é raro** em estágio. Greenhouse e Lever só rendem se você configurar empresas.
- **Adzuna** manda só um trecho da descrição e pode repetir vagas que já vieram da Gupy. Não traz
  salário.
- **Custo de vida** é uma tabela de estimativas, não um dado oficial. A "sobra" só é calculada
  quando a vaga informa salário.
- **E-mails:** a classificação é por regras sobre o assunto. Assuntos genéricos ficam como "verificar"
  de propósito. O nome da empresa é um palpite (às vezes é o nome do recrutador).
- **Nome de empresa na Gupy** às vezes vem com slogan ou nome do programa.
- **A data de formatura** usada nos textos é a do `profile.yaml`. Mantenha-a coerente com o seu
  plano real.

---

## 14. Estrutura de pastas

```
job-hunter/
├── jobhunter/            código
│   ├── collectors/       Gupy, Adzuna, Remotive, Greenhouse, Lever
│   ├── daily.py          rotina completa
│   ├── apply.py          login, fill, mark, status, check, gaps
│   ├── bot.py            bot do Telegram
│   └── ...               filtros, notas, textos, PDF, planilha, e-mails
├── tests/                testes automáticos
├── config/               custo de vida e fontes de vagas (podem ir para o Git)
├── profile/              *.example.yaml vão para o Git; os arquivos reais, não
├── credentials/          chaves do Google (fora do Git)
├── data/                 banco jobs.db, sessão do navegador, logs (fora do Git)
├── output/               uma pasta por candidatura preparada (fora do Git)
│   └── gupy_12345/       candidatura.md, draft.json, curriculo.pdf
└── .env                  chaves e tokens (fora do Git)
```

---

## 15. Desenvolvimento

```powershell
ruff check .          # estilo e erros comuns (limite de 100 colunas por linha)
pytest                # testes (os de navegador são pulados se o Chromium não existir)
```

- Mensagens de commit seguem o padrão `feat:`, `fix:`, `docs:`, `chore:`, `ci:`.
- Rode `ruff check . && pytest` antes de cada commit.
- Cada fonte de vagas é um `Collector` (`jobhunter/collectors/base.py`): implemente `fetch()` e
  devolva objetos `Job`. A deduplicação por id acontece no banco.
- Os testes não chamam serviços reais: usam respostas simuladas (`respx` para HTTP e classes falsas
  para Telegram, Gmail e planilha).