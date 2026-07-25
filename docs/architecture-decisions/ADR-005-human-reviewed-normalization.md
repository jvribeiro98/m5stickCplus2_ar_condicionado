# ADR-005 — Normalização determinística com revisão humana

Status: aceita  
Data: 2026-07-25

## Contexto

O inventário Flipper-IRDB contém centenas de milhares de sinais, milhares de duplicatas e arquivos específicos, universais, bruteforce, mistos e malformados. Nomes de pastas, marcas, modelos e comandos são inconsistentes. Aplicação automática destrutiva propagaria erros para o catálogo OpenIR.

## Decisão

Criar uma fase separada que lê relatórios e produz propostas. Regras são locais, versionadas, determinísticas e explicáveis. Cada sugestão preserva original, candidato, confiança, regra, evidência, conflitos e necessidade de revisão.

Nenhum arquivo `.ir` é modificado. Nenhum Device ou Signal é criado. Valores ambíguos permanecem `null` e entram em fila humana.

## Consequências positivas

- Resultados reproduzíveis e auditáveis.
- Regras podem ser revisadas antes de afetar dados.
- Ambiguidades ficam visíveis.
- Inventário original e contexto são preservados.
- Testes sintéticos não dependem do acervo completo.

## Consequências negativas

- A fila humana pode ser grande.
- Regras conservadoras deixam muitos valores sem classificação.
- Novos formatos de relatório exigem adapters e fixtures.
- Confiança é heurística explicável, não modelo estatístico calibrado.

## Alternativas consideradas

- Aplicação automática sobre `.ir`: rejeitada por ser destrutiva.
- Classificação por pasta: rejeitada por evidência insuficiente.
- LLM ou pesquisa externa: rejeitada por não determinismo e falta de auditabilidade.
- Fuzzy matching automático de marcas: rejeitado pelo risco de fusões incorretas.
- Conversão direta para OpenIR: adiada até revisão das propostas e das licenças.
