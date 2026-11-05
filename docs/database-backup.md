# Backup antes da migração

O TraceLab não recria o banco durante a atualização. Antes de executar `alembic upgrade head`:

1. Encerre backend e frontend para impedir novas gravações.
2. Localize o arquivo SQLite configurado por `TRACELAB_DATABASE_URL` (o padrão é `backend/data/tracelab.db`).
3. Crie uma cópia consistente com `sqlite3 backend/data/tracelab.db ".backup 'backend/data/tracelab-before-findings.db'"`.
4. Copie também o diretório configurado por `TRACELAB_EVIDENCE_STORAGE_PATH`.
5. Valide a cópia com `sqlite3 backend/data/tracelab-before-findings.db "PRAGMA integrity_check;"`; o resultado deve ser `ok`.
6. Execute `poetry run alembic upgrade head` a partir de `backend/`.

A migração mantém os campos legados, relatórios Markdown editados e arquivos de evidência. Evidências antigas ficam como gerais até associação manual. Tabelas de módulos de IA removidos são arquivadas com o prefixo `legacy_`, sem rotas ou código ativo, para que dados históricos também não sejam apagados. Não execute a migração contra a única cópia do banco.
