# ADR-004 — Proveniência e licença por Signal

Status: aceita  
Data: 2026-07-25

## Contexto

Signals compartilhados podem vir de fontes e licenças diferentes do Device. Uma licença no Device não pode autorizar silenciosamente dados importados.

## Decisão

Cada Signal carrega source, licença, contribuidores, confiança, evidência, hash e caminho original, commit e data de captura. Valores desconhecidos são `null`, nunca inventados.

Bundle só declara licença única quando todos os registros forem compatíveis. Caso contrário, preserva licenças individuais e usa `bundle_license: null`.

## Consequências positivas

- Auditoria por Signal.
- Importações preservam cadeia de custódia.
- Redistribuição pode ser decidida com informação explícita.
- Device não “lava” licença de conteúdo.

## Consequências negativas

- Metadados aumentam de tamanho.
- Licenças desconhecidas bloqueiam publicação livre.
- Compatibilidade de licenças exige revisão humana.
- Fontes antigas podem permanecer não distribuíveis.

## Alternativas consideradas

- Uma licença por Device: rejeitada porque Signals são compartilháveis.
- Uma licença obrigatória por catálogo: rejeitada por incompatibilidade entre fontes.
- Assumir CC0 para capturas: rejeitada por inventar direitos não comprovados.
