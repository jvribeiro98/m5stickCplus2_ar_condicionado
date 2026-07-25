# Comparação da normalização v2 → v3

- Registros comparáveis: 8901
- Falsos mistos corrigidos: 107
- Marcadores universais corrigidos: 27
- Modelos `Unknown_*` limpos ou descartados: 936
- Novos casos mistos para auditoria: 4
- Casos universais perdidos para auditoria: 0

## Distribuição por classe

| Classe | v2 | v3 | Diferença |
|---|---:|---:|---:|
| `brute_force` | 192 | 214 | +22 |
| `device_family` | 2672 | 3453 | +781 |
| `malformed` | 11 | 11 | +0 |
| `mixed_collection` | 108 | 5 | -103 |
| `specific_device` | 950 | 153 | -797 |
| `test_or_sample` | 3 | 3 | +0 |
| `universal_remote` | 26 | 53 | +27 |
| `unknown` | 4939 | 5009 | +70 |

## Exemplos de falsos mistos corrigidos

- `Bidet/BioBidet/BioBidet_BB-2000.ir`: `mixed_collection` → `unknown`
- `Bidet/BioBidet/biobidet_bb2000.ir`: `mixed_collection` → `unknown`
- `Bidet/Brandell/BRANDELL_DR802.ir`: `mixed_collection` → `unknown`
- `Blu-Ray/Sony/Sony_BDP-N460_Blu-Ray.ir`: `mixed_collection` → `device_family`
- `Blu-Ray/Sony/Sony_BDP-S370.ir`: `mixed_collection` → `device_family`
- `Clocks/Xflyee/Xflyee_Wallclock_All_Models.ir`: `mixed_collection` → `universal_remote`
- `DVD_Players/Sony/Sony_BDP-S370.ir`: `mixed_collection` → `device_family`
- `Miscellaneous/Gym_HIIT/GX-IR03_Clock.ir`: `mixed_collection` → `unknown`
- `Miscellaneous/Roland/Roland_SC55_SB55.ir`: `mixed_collection` → `unknown`
- `Projectors/BenQ/BenQ_TK800M.ir`: `mixed_collection` → `device_family`

## Exemplos de precedência universal corrigida

- `Blu-Ray/Panasonic/Universal_Region_Unlock/Panasonic_Region_Unlock.ir`: `device_family` → `universal_remote`
- `Clocks/Xflyee/Xflyee_Wallclock_All_Models.ir`: `mixed_collection` → `universal_remote`
- `DVD_Players/Panasonic/Universal_Region_Unlock/Panasonic_Region_Unlock.ir`: `device_family` → `universal_remote`
- `LED_Lighting/tuffenough/tuffenough_all_models.ir`: `device_family` → `universal_remote`
- `Projectors/BrandUnknown/Generic_Universal_Remote.ir`: `device_family` → `universal_remote`
- `Universal_TV_Remotes/EHP/EHP_Waagen_Universal_Remote.ir`: `device_family` → `universal_remote`
- `Universal_TV_Remotes/One_For_All/OFA_8_Universal_Remote.ir`: `device_family` → `universal_remote`
- `Universal_TV_Remotes/Sanyo/Sanyo_universal.ir`: `device_family` → `universal_remote`
- `_Converted_/CSV/P/Philips/Unknown_Philips-PMDVD6T-Universal-AUX/64,47.ir`: `specific_device` → `universal_remote`
- `_Converted_/CSV/U/Universal/Unknown_001/4,15.ir`: `specific_device` → `universal_remote`

## Exemplos de modelos `Unknown_*`

- `ACs/Lamborghini/Unknown_Model_1.ir`: `Unknown_Model_1` → `Model_1`
- `TVs/TCL/TCL_UnknownModel1.ir`: `UnknownModel1` → `UnknownModel1`
- `TVs/TCL/TCL_UnknownModel2.ir`: `UnknownModel2` → `UnknownModel2`
- `TVs/TCL/TCL_UnknownModel3.ir`: `UnknownModel3` → `UnknownModel3`
- `TVs/Thomson/Thomson_UnknownModel1.ir`: `UnknownModel1` → `UnknownModel1`
- `VCR/Unknown/Unknown1.ir`: `Unknown1` → `Unknown1`
- `_Converted_/CSV/A/Acer/Unknown_AT3201W/97_99.ir`: `Unknown_AT3201W` → `AT3201W`
- `_Converted_/CSV/A/Acer/Unknown_RC-802/16_37.ir`: `Unknown_RC-802` → `RC-802`
- `_Converted_/CSV/A/Aconatic/Unknown_AN-2121/2_-1.ir`: `Unknown_AN-2121` → `AN-2121`
- `_Converted_/CSV/A/Acorp/Unknown_Acorp-878/134_107.ir`: `Unknown_Acorp-878` → `Acorp-878`

## Possíveis regressões para auditoria

### Novos casos mistos

- `_Converted_/IR_Plus/S/SEG/LED-TV.ir`: `device_family` → `mixed_collection`
- `_Converted_/IR_Plus/T/TEAC/LED-TV.ir`: `device_family` → `mixed_collection`
- `_Converted_/IR_Plus/T/TELESYSTEM/PALCO 19-LED 01.ir`: `device_family` → `mixed_collection`
- `_Converted_/IR_Plus/T/TELESYSTEM/PALCO-22-LED-04.ir`: `device_family` → `mixed_collection`

### Universais que deixaram de ser universais

- Nenhum caso.

Relatório gerado deterministicamente a partir dos artefatos v2 e v3.
