# ADR-001 — Separar Signal, Binding e Device

Status: aceita  
Data: 2026-07-25

## Contexto

A modelagem inicial colocava semântica, transmissão e ação no mesmo Command. Isso duplicava dados, tornava stateful ambíguo e impedia que aparelhos compartilhassem um Signal.

## Decisão

Separar quatro entidades:

- Capability define significado independente de fabricante;
- Signal define representação IR transmissível;
- Binding liga ação do Device a Signal ou operação stateful;
- Device agrega identidade, Capabilities, Bindings e State Model.

Command fica deprecated e existe somente para migração.

## Consequências positivas

- Deduplicação global de Signals.
- Semântica não depende do protocolo.
- Um stateful Signal pode representar várias propriedades.
- Devices pequenos e pacotes seletivos.
- Compatibilidade pode ser medida por Bindings e Signals.

## Consequências negativas

- Consumidores precisam resolver referências.
- Validação exige invariantes entre documentos.
- Migração dos primeiros registros é obrigatória.
- Mais tipos de entidade aumentam a curva de aprendizado.

## Alternativas consideradas

- Manter Command monolítico: rejeitada por duplicação e ambiguidade.
- Colocar Signals diretamente no Device: mantida apenas para bundles, não para catálogo.
- Tratar Capability como botão: rejeitada porque botões variam por fabricante.
