# Silver benchmark da normalização OpenIR

- Casos: 1219
- Cobertura: 13.70%
- Acurácia: 16.57%
- Erros com confiança ≥ 0,80: 2
- Erros com confiança ≥ 0,95: 1

## Métricas por classe

| Classe | Exemplos | Status | Precisão | Recall | F1 |
|---|---:|---|---:|---:|---:|
| `brute_force` | 1 | insufficient | — | — | — |
| `device_family` | 135 | sufficient | 0.121 | 0.874 | 0.213 |
| `malformed` | 11 | insufficient | — | — | — |
| `specific_device` | 1025 | sufficient | 1.000 | 0.026 | 0.051 |
| `test_or_sample` | 3 | insufficient | — | — | — |
| `universal_remote` | 44 | sufficient | 0.978 | 1.000 | 0.989 |

## Matriz de confusão

| Esperado \ Previsto | `brute_force` | `device_family` | `malformed` | `specific_device` | `test_or_sample` | `universal_remote` | `unknown` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `brute_force` | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `device_family` | 1 | 118 | 0 | 0 | 0 | 0 | 16 |
| `malformed` | 0 | 0 | 11 | 0 | 0 | 0 | 0 |
| `specific_device` | 0 | 855 | 0 | 27 | 0 | 0 | 143 |
| `test_or_sample` | 1 | 0 | 0 | 0 | 2 | 0 | 0 |
| `universal_remote` | 0 | 0 | 0 | 0 | 0 | 44 | 0 |

## Casos por regra

- `brute.marker_confirmed_by_content.v1`: 1
- `family.brand_without_model.v1`: 135
- `malformed.inventory_parse_error.v1`: 11
- `sample.explicit_path_segment.v1`: 3
- `specific.brand_model_filename.v1`: 1025
- `universal.dedicated_directory.v1`: 6
- `universal.explicit_marker.v1`: 38

As referências são derivadas antes da associação com a classificação prevista.
Classes com menos de 20 exemplos são marcadas como amostra insuficiente.
