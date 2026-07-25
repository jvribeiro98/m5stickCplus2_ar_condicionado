# OpenIR

OpenIR é um padrão aberto para descrever dispositivos controlados por infravermelho de forma portátil, validável e independente de fabricante ou plataforma.

O modelo separa:

- **Capability** — significado semântico;
- **Binding** — ação oferecida por um Device;
- **Signal** — representação IR global e deduplicável;
- **Device** — modelo/família e suas associações.

Comece pela [especificação OpenIR v1](docs/specification.md).

O repositório contém:

- schemas JSON Schema Draft 2020-12 em `schemas/`;
- exemplos em `examples/`;
- decisões arquiteturais em `docs/architecture-decisions/`;
- validação automatizada em `tests/`.

O sketch M5Stick existente foi preservado como trabalho anterior e não define a arquitetura do padrão.

## Validação

Instale as dependências de desenvolvimento declaradas em `pyproject.toml` e execute:

```text
pytest
```

Nenhum dado demonstrativo deve ser tratado como captura verificada de um aparelho real.
