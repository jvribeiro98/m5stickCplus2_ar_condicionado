# OpenIR Specification 1.0 — revisão arquitetural

Status: proposta normativa

Schema: JSON Schema Draft 2020-12

Linha compatível: `openir_version: "1.0"`

## 1. Escopo e linguagem normativa

OpenIR é um padrão aberto para descrever dispositivos controlados por infravermelho. Ele define dados portáteis; não define API, banco, parser, importador, firmware, interface ou implementação de encoder.

**DEVE**, **NÃO DEVE**, **DEVERIA**, **NÃO DEVERIA** e **PODE** são termos normativos. Os schemas definem estrutura; este documento define semântica e invariantes entre registros.

## 2. Os quatro conceitos fundamentais

### 2.1 Capability

Uma **Capability** é uma função semântica independente de fabricante, protocolo e botão físico: `volume_up`, `power`, `temperature`, `mode` ou `fan_speed`.

Seu `id` é canônico em `snake_case`. `display_name` e `aliases` existem para apresentação e busca. Um alias nunca substitui o ID armazenado.

### 2.2 Binding

Um **Binding** é uma ação exposta por um Device. Ele liga uma Capability a:

- um `signal_ref`, para transmissão direta; ou
- uma `state_operation`, para aplicar snapshot ou solicitar codificação de estado.

Bindings representam intenção e interação, não os timings IR. Exemplos:

- incrementar `volume_up`;
- selecionar `input` com `enum_value: hdmi_1`;
- definir `temperature` com `value: 23`;
- alternar energia;
- aplicar um snapshot stateful.

`interaction_type` possui: `trigger`, `toggle`, `set_value`, `increment`, `decrement`, `select` e `state_update`.

Um Binding pode sobrescrever a repetição padrão do Signal. Se `repeat` for `null`, vale a política do Signal.

### 2.3 Signal

Um **Signal** é uma representação IR transmissível e globalmente deduplicável. Vários Devices podem referenciar o mesmo Signal sem copiar seus timings.

Tipos:

- `protocol`: protocolo conhecido e parâmetros decodificados;
- `raw`: pulsos e espaços originais;
- `state_snapshot`: quadro associado explicitamente a um estado completo;
- `encoder_reference`: metadados de um encoder stateful;
- `opaque`: captura transmissível cujo significado ainda não foi decodificado.

Signal não possui `canonical_name`: uma única transmissão stateful pode representar simultaneamente muitas Capabilities, e o mesmo Signal pode ter funções diferentes conforme o Device.

### 2.4 Device

Um **Device** representa modelo ou família com o mesmo comportamento IR. Ele contém identidade, Capabilities, Bindings, State Model, compatibilidade e seus próprios metadados editoriais.

O Device canônico não incorpora Signals. Ele os referencia por IDs em seus Bindings. Um bundle offline pode incorporar os Signals referenciados.

## 3. Identidade e deduplicação de Signals

### 3.1 ID endereçado por conteúdo

O formato é:

`signal-sha256-<64 caracteres hexadecimais minúsculos>`

O hash é SHA-256 dos bytes UTF-8 da representação canônica do **material de identidade**.

### 3.2 Material de identidade

O material de identidade é um objeto formado, nesta ordem conceitual, por:

1. `signal_type`;
2. `frequency`;
3. `protocol`;
4. `raw_data`;
5. `state_snapshot`;
6. `encoder_reference`;
7. `repeat`.

Os campos `id`, proveniência, licença, contribuidores, confiança, evidências, caminhos, commits, datas e extensões NÃO entram no hash. Assim, melhorar metadados não cria outro Signal.

### 3.3 Canonicalização

Antes do SHA-256, o material de identidade DEVE ser serializado conforme JSON Canonicalization Scheme, RFC 8785:

- UTF-8;
- nomes de propriedades ordenados segundo JCS;
- sem whitespace insignificante;
- strings e números na forma JCS;
- arrays preservam ordem;
- `null` permanece explícito.

Uma implementação que não suporte JCS NÃO DEVE publicar IDs canônicos. Pode trabalhar com Signals existentes.

### 3.4 RAW exato e RAW normalizado

`raw_data.original` é a captura preservada. `raw_data.normalized` é uma derivação opcional para comparação ou transmissão tolerante.

O RAW original:

- DEVE usar durações positivas em microssegundos;
- DEVE começar por mark e alternar mark/space;
- NÃO DEVE ser substituído, arredondado ou sobrescrito;
- DEVE permanecer disponível mesmo quando houver versão normalizada.

Normalização pode reduzir jitter, agrupar durações próximas e ajustar valores nominais. Ela cria informação derivada, nunca nova evidência. O Signal ID inclui original e normalizado; alterar qualquer um cria outro ID. Ferramentas de deduplicação podem manter, além do ID exato, índices de similaridade normalizada que não são identidade canônica.

Dois RAWs normalizados como semelhantes não devem ser mesclados automaticamente. A deduplicação exata ocorre por ID; deduplicação provável exige revisão e preservação de ambos os originais.

### 3.5 Signal canônico, referência e embedded

- **Canonical Signal**: registro validado, armazenado uma vez no catálogo pelo ID.
- **Signal reference**: `signal_ref` em um Binding; é a forma canônica dentro do Device.
- **Embedded Signal**: cópia integral em `bundle.signals`, com o mesmo ID e conteúdo do canônico.

Embedded não cria identidade nova. Um consumidor DEVE rejeitar um embedded Signal cujo conteúdo não corresponda ao ID declarado.

## 4. Proveniência, confiança e licença por Signal

Cada Signal DEVE possuir individualmente:

- `source`;
- `license`;
- `contributors`;
- `confidence`;
- `evidence`;
- `original_hash`;
- `original_path`;
- `source_commit`;
- `captured_at`.

Campos desconhecidos usam `null`; não devem receber valores inventados. Em importações futuras, `original_hash` deve identificar o arquivo-fonte antes de conversão, e `original_path` deve preservar o caminho relativo na origem. `source_commit` identifica o commit quando conhecido.

`confidence` varia de 0 a 1:

| Faixa | Interpretação |
|---|---|
| 0,00–0,24 | gerado, relatado ou não reproduzido |
| 0,25–0,49 | captura/decodificação preliminar |
| 0,50–0,74 | testado em ao menos uma unidade |
| 0,75–0,89 | reproduzido independentemente |
| 0,90–1,00 | múltiplos testes, evidência e revisão |

Confiança não é votação nem probabilidade matemática.

Licença desconhecida é representada por `spdx_id: null`, nome explicativo e URL opcional. Isso mantém o registro validável, mas NÃO autoriza redistribuição. Conteúdo importado nunca deve ser marcado automaticamente como CC0, MIT ou livre.

A licença do Device cobre seus metadados, não substitui licenças de Signals. Um bundle só pode preencher `bundle_license` quando todos os registros forem compatíveis com ela. Caso contrário, `bundle_license` deve ser `null` e cada licença individual deve ser preservada.

## 5. Protocolos e representação IR

### 5.1 Protocol

Protocol contém identidade, variante, modelo de estado e parâmetros portáteis. Nomes de bibliotecas e funções não são IDs de protocolo.

`state_model` pode ser `stateless`, `stateful` ou `hybrid`.

### 5.2 Signal protocol

Um Signal `protocol` exige `protocol`. Seus parâmetros devem ser suficientes para uma implementação compatível gerar o quadro. Pode incluir RAW original como evidência redundante.

### 5.3 Signal raw

Um Signal `raw` exige `raw_data.original`. Cada item é inteiro positivo; zero e negativos são inválidos. `frequency` é hertz, `sequence` é microssegundos e `duty_cycle` é fração ou `null`.

### 5.4 Opaque

`opaque` preserva captura transmissível sem atribuir semântica não comprovada. Ele exige RAW original. Não é um escape para extensões arbitrárias.

O antigo `encoding_type: future` foi removido. Conteúdo experimental usa `extensions` com chaves `x-<organização>-<nome>`. Consumidores devem ignorar extensões desconhecidas e não devem transmitir conteúdo experimental que não compreendam.

## 6. Stateful

### 6.1 State Model do Device

Devices stateful declaram `state_model` com:

- propriedades e tipos;
- campos obrigatórios;
- valores permitidos;
- intervalos e passos;
- unidade;
- valor padrão, quando conhecido;
- dependências;
- combinações inválidas conhecidas.

Constraints são declarativas. Elas não contêm código executável.

### 6.2 Captured state snapshot

Um Signal `state_snapshot` possui `state_snapshot.state`, por exemplo energia, temperatura, modo, ventilação, swing, turbo e sleep ao mesmo tempo. Ele também deve possuir representação transmissível protocolada ou RAW.

O snapshot é fixo. Alterar qualquer campo de estado produz outro material de identidade e outro Signal ID.

### 6.3 Stateful encoder reference

Um Signal `encoder_reference` contém somente:

- `encoder_id`;
- `protocol_id`;
- `encoder_version`;
- `required_state_fields`;
- `optional_state_fields`.

Não contém firmware, biblioteca, bytecode ou código. O consumidor só pode executar `encode_state` se possuir implementação compatível do mesmo encoder e versão. Caso contrário, deve usar snapshots transmitíveis disponíveis ou informar que a ação não é suportada.

### 6.4 State operation

Bindings stateful usam:

- `apply_snapshot`: transmite snapshot fixo;
- `encode_state`: solicita ao encoder compatível um quadro para o estado;
- `update_fields`: aplica campos sobre estado conhecido segundo a implementação compatível.

O estado solicitado deve respeitar o State Model.

## 7. Bindings em detalhe

Todo Binding possui `id`, `capability_id`, `interaction_type`, `signal_ref` ou `state_operation`, `parameters`, `aliases`, `repeat` e `notes`.

Exatamente um entre `signal_ref` e `state_operation` deve ser usado.

Padrões:

| Caso | Interaction | Representação |
|---|---|---|
| Pressionar volume + | `increment` | `signal_ref` |
| Alternar power | `toggle` | `signal_ref` |
| HDMI 1 | `select` | `parameters.enum_value: hdmi_1` + `signal_ref` |
| Temperatura 23 capturada | `state_update` | `apply_snapshot` |
| Temperatura variável | `set_value` | `encode_state` |

`capability_id` deve existir em `device.capabilities`. IDs de Binding são locais ao Device e começam com `binding-`.

## 8. Migração de Command

A primeira versão confundia Command, Signal e Capability. `command.schema.json` permanece no repositório, explicitamente deprecated, apenas para leitura e migração.

Migração:

1. Extraia protocolo, RAW, state snapshot ou encoder para um Signal.
2. Canonicalize o material de identidade e calcule o Signal ID.
3. Preserve proveniência e licença no Signal, sem inventá-las.
4. Converta `canonical_name` em `capability_id`.
5. Crie Binding com interaction adequada e `signal_ref`/`state_operation`.
6. Mova repetição específica da ação para o Binding; mantenha a repetição física padrão no Signal.
7. Remova o Command do Device somente após verificar as referências.

Novos dados NÃO DEVEM usar Command. A remoção física do schema só pode ocorrer em uma futura major.

## 9. Device, IDs e aliases

Device ID:

`<category-com-hifens>-<brand-id>-<model-slug>`

Exemplos: `tv-samsung-au7700` e `air-conditioner-daikin-ftxm35`.

IDs publicados não são reciclados. Correção do conteúdo mantém ID e incrementa `version`; correção de identidade cria outro ID e usa `supersedes`.

Aliases passam por NFKC, trim e comparação case-insensitive. Espaço, hífen e underscore podem ser equivalentes na busca. Símbolos como `+` e `-` devem ser preservados antes do mapeamento. Assim, `VOL+`, `Volume+`, `Vol Up` e `volume_up` podem resolver para `volume_up`. Aliases não são chaves únicas.

Categorias iniciais: `tv`, `air_conditioner`, `fan`, `projector`, `receiver`, `soundbar`, `led_strip`, `camera`, `light`, `media_player` e `other`.

## 10. Compatibilidade baseada em evidência

Compatibilidade é direcional e possui:

- `target_device_id`;
- `relation`;
- `scope`;
- `confidence`;
- `evidence`;
- `tested_commands` (IDs de Binding legados no nome do campo);
- `tested_signals`;
- `notes`;
- `tested_at`.

`scope`: `full`, `partial`, `command_subset`, `signal_subset` ou `unknown`.

Compartilhar um Signal só comprova aquele Signal. Nunca comprova compatibilidade total. `full` exige cobertura representativa de todos os Bindings e states relevantes. A relação A → B não cria automaticamente B → A.

## 11. Submission e contribuição

Submission é o envelope auditável de contribuição. Registra submitter, ação, alvo, payload, evidências, confiança, licença declarada, atestação e revisão.

Uma Submission aceita cria nova versão imutável do registro. Captura, importação, teste e revisão devem permanecer atribuíveis. Dados sem direitos claros podem ser preservados para análise privada, mas não publicados como livres.

## 12. Bundles e distribuição

Bundle possui três perfis:

- `metadata`: apenas identificação e lista de Signals necessários;
- `device`: metadados e Device com Capabilities/Bindings, sem Signals;
- `offline`: Device e exatamente o subconjunto de Signals necessário.

Um firmware pode, portanto:

1. baixar metadata para descoberta;
2. baixar Device e examinar seus Bindings;
3. comparar `included_signal_ids` com cache local;
4. baixar somente Signals ausentes;
5. usar bundle `offline` quando não haverá rede.

O transporte não é definido. Bundles preservam IDs, versões, licenças e hash de conteúdo. A validação semântica deve garantir que todos os `signal_ref` do Device offline resolvam dentro do bundle e que não existam Signals não declarados no metadata.

## 13. Versionamento

A especificação e cada registro usam Semantic Versioning.

Especificação:

- major: quebra incompatível;
- minor: adição compatível;
- patch: esclarecimento.

Device:

- major: mudança incompatível de Binding/semântica;
- minor: novas capabilities, bindings ou compatibilidades;
- patch: correção editorial/evidência.

Signals são imutáveis por serem endereçados por conteúdo. Mudança no material de identidade gera novo ID; mudança apenas em metadados pode atualizar o registro editorial sem mudar o ID.

## 14. Extensões e segurança

Extensões usam `x-<organização>-<nome>`, são versionadas por seu proprietário e não alteram campos normativos. Campos desconhecidos fora de `extensions` invalidam o documento.

Consumidores:

- devem validar antes de transmitir;
- devem impor limites locais de frequência, duração e repetição;
- não devem executar encoder desconhecido;
- não devem transmitir extensões desconhecidas;
- devem tratar texto e URI como não confiáveis;
- devem verificar identidade de Signals embedded.

## 15. Conformidade

Um catálogo conforme:

1. valida todos os schemas e registros;
2. resolve referências relativas;
3. mantém Signals globais por conteúdo;
4. preserva RAW original e proveniência;
5. verifica que Binding referencia Capability local;
6. verifica que todo Signal referenciado existe;
7. não eleva licenças silenciosamente;
8. não infere compatibilidade total por compartilhamento de Signal.

Um bundle offline conforme contém Device válido, todos e somente os Signals declarados necessários, e preserva licenças por registro.

## 16. Schemas normativos

- `category.schema.json`
- `brand.schema.json`
- `capability.schema.json`
- `protocol.schema.json`
- `signal.schema.json`
- `binding.schema.json`
- `state-model.schema.json`
- `device.schema.json`
- `compatibility.schema.json`
- `submission.schema.json`
- `bundle.schema.json`
- `command.schema.json` (deprecated)

Decisões arquiteturais detalhadas estão em `docs/architecture-decisions/`.
