# Ollama local no Ubuntu

O Ollama é opcional. O TraceLab não instala o servidor nem baixa modelos automaticamente, não usa API comercial e continua funcionando normalmente quando a IA está desligada ou indisponível.

## Requisitos e escolha do modelo

O modelo inicial configurado é `qwen3-vl:2b`. O catálogo do Ollama informa aproximadamente 1,9 GB para esse artefato e suporte a texto e imagem. Em uma máquina com cerca de 8 GB de RAM e sem GPU dedicada, use apenas uma geração por vez e feche outros processos pesados. O desempenho em CPU será inferior ao de uma GPU.

Consulte a página oficial do modelo antes do download: <https://ollama.com/library/qwen3-vl/tags>.

## Instalação do servidor

Revise o script antes de executá-lo. O comando oficial atual para Linux é:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Depois, verifique o serviço:

```bash
sudo systemctl status ollama
curl http://127.0.0.1:11434/api/version
```

Se a instalação não configurar o serviço, execute `ollama serve` em um terminal separado. Consulte sempre a [documentação oficial para Linux](https://docs.ollama.com/linux) para instalação manual, ARM64 e atualizações.

## Download manual do modelo

O comando abaixo baixa dados da internet e ocupa espaço em disco. Execute-o somente quando decidir instalar o modelo:

```bash
ollama pull qwen3-vl:2b
```

Liste os modelos já instalados sem baixar nada:

```bash
ollama list
```

O TraceLab nunca executa `ollama pull`. Também é possível selecionar outro modelo já instalado na tela **Configurações de IA**. Modelos sem a capacidade `vision` continuam disponíveis para texto, mas são recusados em solicitações com imagens.

## Configuração do TraceLab

Copie `.env.example` para `.env` e ajuste apenas o necessário:

```dotenv
TRACELAB_AI_ENABLED=true
TRACELAB_OLLAMA_BASE_URL=http://127.0.0.1:11434
TRACELAB_OLLAMA_MODEL=qwen3-vl:2b
TRACELAB_OLLAMA_TIMEOUT_SECONDS=120
TRACELAB_OLLAMA_KEEP_ALIVE=5m
TRACELAB_AI_MAX_IMAGES=4
TRACELAB_AI_MAX_IMAGE_BYTES=10485760
TRACELAB_AI_MAX_IMAGE_DIMENSION=1600
```

`TRACELAB_OLLAMA_KEEP_ALIVE` controla por quanto tempo o modelo permanece carregado depois de uma geração. Use `0` para descarregá-lo imediatamente e economizar memória, ao custo de maior latência na próxima operação. A [API de geração do Ollama](https://docs.ollama.com/api/generate) documenta `keep_alive` e o envio de imagens em Base64.

A preferência habilitado/desabilitado e o modelo escolhido pela interface são persistidos em `backend/data/ai-settings.json`, que é local e ignorado pelo Git. Variáveis de ambiente definem o servidor, timeout e limites.

## Endpoints do TraceLab

- `GET /api/ai/status`: disponibilidade, versão e capacidade do modelo selecionado;
- `GET /api/ai/models`: modelos instalados e capacidades;
- `GET/PATCH /api/ai/settings`: preferências locais;
- `POST /api/ai/test-connection`: teste explícito do servidor;
- `POST /api/ai/test-generation`: teste explícito de texto;
- `POST /api/ai/generate/text`: geração de texto;
- `POST /api/ai/generate/images`: prompt e imagens via multipart;
- `DELETE /api/ai/operations/current`: cancelamento da geração ativa.

As gerações não são iniciadas automaticamente. Há no máximo uma operação em andamento; uma segunda solicitação recebe HTTP 409. Imagens PNG, JPEG e WebP são validadas, deduplicadas e reduzidas proporcionalmente quando excedem a dimensão configurada.

## Diagnóstico

Se a tela indicar indisponibilidade:

```bash
sudo systemctl status ollama
journalctl -e -u ollama
curl http://127.0.0.1:11434/api/tags
```

Confirme também que `TRACELAB_OLLAMA_BASE_URL` aponta para o servidor local correto. Nenhuma chave é necessária para a API local padrão, cujo endereço oficial é `http://localhost:11434/api`.
