# ADR-003 — Representação stateful

Status: aceita  
Data: 2026-07-25

## Contexto

Ar-condicionado e aparelhos semelhantes transmitem energia, temperatura, modo, ventilação e outros estados em um único quadro. Associar esse quadro a um único `canonical_name` produz informação incorreta.

## Decisão

Device declara State Model. Signal stateful é:

- snapshot capturado com estado explícito e forma transmissível; ou
- referência portátil de encoder, sem código executável.

Binding usa `apply_snapshot`, `encode_state` ou `update_fields`. Encoder reference só é executável por consumidor que implemente o mesmo ID e versão.

## Consequências positivas

- Estado multivariável fica explícito.
- Snapshots funcionam em consumidores simples.
- Encoders evitam matrizes enormes de combinações.
- JSON permanece independente de firmware e linguagem.

## Consequências negativas

- Catálogos podem precisar de muitos snapshots.
- Consumidores sem encoder suportam apenas estados capturados.
- Dependências e combinações inválidas exigem modelagem cuidadosa.
- Compatibilidade stateful demanda testes combinatórios.

## Alternativas consideradas

- Um Command por propriedade: rejeitada porque o quadro não é independente.
- Código de encoder dentro do JSON: rejeitada por portabilidade e segurança.
- Apenas RAW: possível para snapshots, insuficiente para estado parametrizável.
