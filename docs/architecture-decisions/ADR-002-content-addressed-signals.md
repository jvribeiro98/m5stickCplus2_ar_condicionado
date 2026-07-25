# ADR-002 — Signals endereçados por conteúdo

Status: aceita  
Data: 2026-07-25

## Contexto

Um catálogo com aproximadamente 300 mil sinais precisa detectar cópias exatas, preservar referências estáveis e evitar timings repetidos em cada Device.

## Decisão

Signal ID usa `signal-sha256-<hash>`. O SHA-256 é calculado sobre material de identidade serializado por JCS/RFC 8785. Metadados, proveniência e licença não entram no hash.

RAW original e normalizado coexistem. O original nunca é sobrescrito. Similaridade normalizada pode produzir candidatos, mas não funde Signals automaticamente.

## Consequências positivas

- Deduplicação exata determinística.
- Integridade verificável em bundles.
- Cache e distribuição incremental eficientes.
- Metadados podem melhorar sem quebrar referências.

## Consequências negativas

- Publicadores precisam implementar JCS corretamente.
- Pequenas mudanças transmissíveis geram novo ID.
- Capturas equivalentes com jitter ainda exigem análise de similaridade.
- Corrigir material de identidade exige atualizar referências.

## Alternativas consideradas

- UUID aleatório: estável, mas não deduplica conteúdo.
- Hash somente do RAW normalizado: rejeitado por risco de colisão semântica e perda de captura.
- Hash do documento inteiro: rejeitado porque licença e evidência mudariam a identidade física.
