# OpenIR Specification 1.0

Status: proposta normativa inicial  
Versão da especificação: 1.0.0  
Identificador de documentos conformes: `openir_version: "1.0"`  
Idioma normativo desta edição: português do Brasil

## 1. Propósito

OpenIR é um formato aberto, portátil e independente de plataforma para descrever dispositivos controlados por infravermelho. Seu papel é equivalente ao de uma descrição de interface: definir significado, identidade, codificação, proveniência e compatibilidade sem impor firmware, linguagem, biblioteca, transporte, banco de dados ou interface gráfica.

Um documento OpenIR deve poder ser consumido, total ou parcialmente, por microcontroladores, computadores, sistemas de automação residencial, aplicativos móveis, ferramentas de teste e dispositivos especializados.

OpenIR v1 tem quatro objetivos:

1. Dar o mesmo significado a uma ação em fabricantes diferentes.
2. Preservar informação suficiente para reproduzir uma transmissão IR.
3. Tornar contribuições comunitárias auditáveis.
4. Permitir evolução sem quebrar consumidores conformes.

## 2. Linguagem normativa

As palavras **DEVE**, **NÃO DEVE**, **OBRIGATÓRIO**, **DEVERIA**, **NÃO DEVERIA** e **PODE** têm sentido normativo. “DEVE” indica requisito de conformidade; “DEVERIA” indica recomendação que pode ser ignorada apenas com justificativa; “PODE” indica opção.

JSON Schema Draft 2020-12 é a linguagem normativa de validação estrutural. O texto desta especificação define as regras semânticas que não podem ser expressas integralmente nos schemas.

## 3. Modelo conceitual

### 3.1 Device

Um **Device** é o perfil canônico de um modelo ou família de modelos que compartilha comportamento IR. Ele agrega identidade comercial, capacidades, comandos, compatibilidade, proveniência, licença e histórico de versão.

Um Device não representa uma unidade física individual, um endereço de rede nem a configuração pessoal de um usuário.

Todo Device DEVE possuir:

- `id`: identidade canônica, estável e global no catálogo;
- `category`: categoria OpenIR;
- `brand`: marca normalizada;
- `model`: modelo como divulgado;
- `aliases`: nomes alternativos do modelo;
- `description`: resumo humano;
- `year`: ano inicial conhecido, ou `null`;
- `region`: regiões de comercialização;
- `manufacturer`: entidade fabricante;
- `capabilities`: vocabulário semântico suportado;
- `commands`: realizações IR dessas capacidades;
- `compatibility`: relações direcionais com outros Devices;
- `contributors`: autoria, captura, teste e revisão;
- `source`: origem, referências e confiança;
- `license`: termos de reutilização;
- `status`: maturidade editorial;
- `version`: versão do registro.

`openir_version` identifica a linha da especificação usada pelo documento e também é obrigatório.

### 3.2 Command

Um **Command** é uma realização transmissível de uma Capability. Ele relaciona a intenção canônica (`canonical_name`) à sua representação física ou lógica.

Um Command DEVE declarar exatamente um `encoding_type`:

- `protocol`: campos decodificados de um protocolo conhecido;
- `raw`: sequência temporal de pulsos e espaços;
- `stateful`: quadro que representa estado completo ou alteração de estado;
- `future`: representação opaca reservada para extensões controladas.

Um Command não é necessariamente um botão. Em aparelhos stateful, ele pode representar um estado parametrizado, um estado-base ou uma transição.

### 3.3 Protocol

Um **Protocol** identifica a família de codificação IR e os parâmetros necessários para produzir um quadro. Exemplos conceituais incluem protocolo, variante, endereço, comando, quantidade de bits e modelo interno.

`state_model` informa se o protocolo é:

- `stateless`: cada comando pode ser entendido isoladamente;
- `stateful`: o quadro descreve o estado do aparelho;
- `hybrid`: possui comandos independentes e quadros de estado.

O nome de uma biblioteca ou de uma função NÃO DEVE ser usado como identidade do protocolo. Implementações PODEM mapear o `id` OpenIR para suas bibliotecas locais.

### 3.4 Capability

Uma **Capability** é uma intenção semântica independente de fabricante, modelo e protocolo, como `volume_up`, `mute`, `temperature_up` ou `swing`.

Capabilities formam o vocabulário de interoperabilidade. O `id` é canônico e não deve conter marca. `display_name` é apenas apresentação. Aliases ajudam descoberta e importação, mas nunca substituem o ID canônico armazenado.

Uma Capability declara seu tipo de valor:

- `trigger`: ação momentânea;
- `boolean`: estado ligado/desligado;
- `integer` ou `number`: valor numérico;
- `string`: texto livre;
- `enum`: conjunto fechado;
- `object`: estado estruturado.

### 3.5 Submission

Uma **Submission** é o envelope de contribuição comunitária. Ela registra quem submeteu, quando, qual ação foi proposta, qual registro é afetado, evidências, confiança declarada, licença, atestação de direitos e estado da revisão.

Submission não é Device. Uma submissão aceita deve gerar uma nova versão do registro canônico, preservando a trilha de auditoria.

## 4. Categorias

OpenIR v1 define inicialmente:

| ID | Significado |
|---|---|
| `tv` | Televisor |
| `air_conditioner` | Ar-condicionado |
| `fan` | Ventilador |
| `projector` | Projetor |
| `receiver` | Receiver de áudio/vídeo |
| `soundbar` | Barra de som |
| `led_strip` | Fita de LED |
| `camera` | Câmera controlada por IR |
| `light` | Luminária |
| `media_player` | Reprodutor de mídia |
| `other` | Categoria ainda não padronizada |

Novas categorias exigem revisão da versão menor da especificação. `other` DEVERIA ser temporário; sua descrição deve explicar a natureza do dispositivo.

## 5. Convenções de IDs

IDs são ASCII minúsculo e estáveis. Espaços, acentos, pontuação e marcas registradas decorativas são normalizados para hífen.

### 5.1 Device ID

Formato:

`<category>-<brand-id>-<model-slug>`

Exemplos:

- `tv-samsung-au7700`
- `air-conditioner-daikin-ftxm35`
- `soundbar-lg-sn4`

Regras:

1. O ID DEVE corresponder a `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
2. O primeiro segmento DEVE ser a categoria, convertendo `_` em `-`.
3. O segundo componente lógico DEVE ser o `brand.id`.
4. O modelo deve preservar números e letras relevantes.
5. Revisões de hardware só entram no ID quando mudam o comportamento IR.
6. Um ID publicado NÃO DEVE ser reciclado para outro aparelho.
7. Correção de identidade exige novo ID e `supersedes`; correção de dados mantém o ID e incrementa `version`.

### 5.2 Command ID

Formato base:

`command-<canonical-name-com-hifens>`

Exemplos:

- `command-volume-up`
- `command-power-on`
- `command-temperature-24-cool-auto`

Quando há mais de uma realização da mesma Capability, o sufixo DEVE distinguir semanticamente variante ou estado. IDs baseados em posição, como `command-01`, NÃO DEVEM ser usados.

### 5.3 Outros IDs

- Brand: slug curto, por exemplo `samsung`.
- Protocol: nome público normalizado, por exemplo `nec` ou `samsung-ac`.
- Capability: `snake_case`, por exemplo `direction_up`.
- Submission: `submission-<ano>-<slug-ou-identificador>`.
- Contributor: identificador estável da comunidade, sem e-mail obrigatório.

## 6. Aliases e normalização

Aliases preservam grafias usadas por fabricantes, usuários e fontes. O valor canônico é sempre o ID.

Para Capability, `VOL+`, `Volume+`, `Vol Up` e `volume_up` podem aparecer em `aliases`, mas todos resolvem para `volume_up`.

Um resolvedor de aliases DEVERIA:

1. aplicar normalização Unicode NFKC;
2. remover espaços nas extremidades;
3. comparar sem diferença entre maiúsculas e minúsculas;
4. tratar sequências de espaços, hífens e sublinhados como separadores equivalentes;
5. preservar símbolos com significado, como `+` e `-`, antes do mapeamento;
6. consultar aliases apenas dentro do contexto apropriado, como categoria ou Capability.

Aliases NÃO DEVEM ser usados como chaves únicas. Colisões são permitidas e devem ser resolvidas pelo contexto. O alias original deve ser preservado para apresentação e auditoria.

## 7. Vocabulário inicial de Capabilities

O catálogo pode crescer de maneira aditiva. Consumidores DEVEM ignorar capabilities desconhecidas sem rejeitar todo o Device.

### 7.1 Capabilities comuns

`power`, `power_on`, `power_off`, `toggle`, `sleep`, `timer`, `eco`, `turbo`, `light`, `display`, `beep`.

`power` deve ser `boolean` quando representa estado desejado. `power_on`, `power_off` e `toggle` são `trigger`.

### 7.2 TV, projector e media_player

`volume_up`, `volume_down`, `mute`, `channel_up`, `channel_down`, `menu`, `home`, `back`, `input`, `direction_up`, `direction_down`, `direction_left`, `direction_right`, `ok`, `guide`, `info`, `subtitle`, `play`, `pause`, `stop`, `rewind`, `fast_forward`, `record`, `previous`, `next`, `exit`, `settings`, `aspect_ratio`, `picture_mode`.

### 7.3 Air conditioner

`temperature`, `temperature_up`, `temperature_down`, `mode`, `fan`, `fan_speed`, `swing`, `swing_horizontal`, `swing_vertical`, `eco`, `turbo`, `sleep`, `timer`, `clean`, `quiet`, `ionizer`, `beep`, `display`.

Valores recomendados de `mode`: `auto`, `cool`, `dry`, `fan`, `heat`. Fabricantes podem possuir valores adicionais por extensão.

### 7.4 Fan

`fan`, `fan_speed`, `speed_up`, `speed_down`, `oscillation`, `breeze`, `direction`, `timer`, `sleep`, `light`.

### 7.5 Receiver e soundbar

`volume_up`, `volume_down`, `mute`, `input`, `sound_mode`, `bass_up`, `bass_down`, `treble_up`, `treble_down`, `subwoofer_up`, `subwoofer_down`, `surround`, `night_mode`, `dialog_enhance`.

## 8. Representação dos comandos

### 8.1 Campos comuns

Todo Command possui:

- `id`: identidade local estável no Device;
- `display_name`: rótulo humano;
- `canonical_name`: Capability realizada;
- `encoding_type`: estratégia de representação;
- `protocol`: protocolo ou `null`;
- `raw_data`: dados temporais ou `null`;
- `parsed_data`: dados decodificados/semânticos ou `null`;
- `repeat`: política de repetição;
- `frequency`: portadora em hertz;
- `notes`: observações ou `null`.

`canonical_name` DEVE corresponder ao `id` de uma Capability declarada no mesmo Device.

### 8.2 Codificação baseada em protocolo

`encoding_type: protocol` exige `protocol` e `parsed_data`. `protocol.parameters` contém os campos necessários ao codificador. Números cujo comprimento ou zeros iniciais sejam semanticamente importantes DEVERIAM ser strings, preferencialmente com notação hexadecimal explícita.

`raw_data` PODE coexistir como captura de referência. Quando as duas representações divergem, um registro verificado DEVE ser rebaixado até revisão; nenhuma representação tem precedência silenciosa.

### 8.3 Codificação RAW

`raw_data.sequence` é uma lista de inteiros positivos em microssegundos. O primeiro item é pulso com portadora (mark), o segundo é espaço sem portadora (space), alternando até o fim.

O registro DEVE declarar `frequency`. `duty_cycle` é uma fração maior que zero e menor ou igual a um, ou `null` quando desconhecido.

Dados RAW:

- NÃO DEVEM conter durações negativas;
- NÃO DEVEM inferir unidade;
- DEVEM preservar a captura mais limpa disponível;
- DEVERIAM resultar de múltiplas capturas comparadas;
- DEVERIAM documentar tolerância e equipamento na evidência da Submission.

### 8.4 Protocolos stateful

Em um protocolo stateful, o receptor normalmente espera um quadro que descreve várias propriedades simultaneamente. OpenIR usa:

- `state_snapshot`: estado autossuficiente;
- `state_delta`: alteração que depende de um `base_state`;
- `opaque`: quadro conhecido, mas ainda não semanticamente decodificado.

Um comando `stateful` DEVE usar protocolo `stateful` ou `hybrid` e `parsed_data` com `state_snapshot` ou `state_delta`.

Snapshots DEVERIAM incluir todos os campos relevantes, inclusive valores desativados, para evitar dependência do estado local do consumidor. Um Device pode conter uma matriz de snapshots comuns ou um protocolo parametrizável. OpenIR descreve os dados; não determina como uma implementação gera combinações não materializadas.

Consumidores incapazes de codificar o protocolo só podem transmitir um comando stateful se houver `raw_data` correspondente ao estado exato. NÃO DEVEM combinar arbitrariamente trechos RAW.

### 8.5 Codificação future

`future` impede que uma representação nova seja confundida com as três conhecidas. O conteúdo deve ser opaco, documentado em extensão namespaced e ignorável por consumidores antigos. Recursos candidatos a padronização não devem ocupar silenciosamente campos existentes.

### 8.6 Repetição

`repeat.count` é o número de transmissões adicionais após a primeira. Logo, zero significa uma transmissão total.

Modos:

- `none`: sem repetição;
- `full_frame`: repete o quadro completo;
- `protocol_repeat_frame`: usa o quadro especial definido pelo protocolo.

`gap` é o intervalo em microssegundos. Um consumidor NÃO DEVE substituir `protocol_repeat_frame` por `full_frame` sem conhecer a equivalência.

## 9. Confiança, origem e status

### 9.1 Nível de confiança

Confiança é um número de 0 a 1:

| Faixa | Interpretação |
|---|---|
| 0,00–0,24 | relato não reproduzido |
| 0,25–0,49 | captura ou derivação preliminar |
| 0,50–0,74 | testado ao menos uma vez no modelo-alvo |
| 0,75–0,89 | reproduzido por fontes ou unidades independentes |
| 0,90–1,00 | evidência forte, revisão e testes repetidos |

Confiança não é probabilidade matemática e NÃO DEVE aumentar apenas por votação. Ela deve refletir qualidade, independência e reprodutibilidade da evidência.

### 9.2 Origem

Valores de `source.origin`:

- `original_capture`: capturado do controle físico;
- `manufacturer_documentation`: fornecido pelo fabricante;
- `community_database`: obtido de outro catálogo;
- `reverse_engineering`: inferido por análise;
- `generated`: produzido a partir de especificação conhecida;
- `converted`: convertido de outro formato;
- `unknown`: origem não recuperável.

Referências devem incluir descrição, URI quando possível e hash quando um artefato estável existir. Conversão não apaga a origem anterior; a cadeia deve permanecer nas referências.

### 9.3 Status editorial

- `draft`: incompleto e não recomendado para uso automático;
- `experimental`: estruturalmente válido, ainda em validação;
- `verified`: testado e revisado;
- `deprecated`: substituído ou não recomendado;
- `rejected`: preservado apenas para impedir reintrodução de dado inválido.

Somente mantenedores podem promover um registro a `verified`, com evidência documentada.

## 10. Licença e direitos

Todo Device e toda Submission DEVE declarar licença por identificador SPDX. A licença cobre o registro, seus metadados e sequências contribuídas, sem afirmar propriedade sobre marcas ou documentação de terceiros.

Contribuidores DEVEM atestar que criaram os dados, possuem permissão ou que a origem permite redistribuição. Dados sem licença clara não podem entrar no catálogo canônico.

Marcas, nomes de modelos e identificadores factuais permanecem propriedade de seus titulares. Sua presença serve apenas à interoperabilidade e não implica afiliação.

## 11. Compatibilidade

Compatibilidade é uma relação **direcional** do Device atual para `compatibility[].device_id`. A afirmação A → B não implica B → A.

Níveis:

- `exact`: mesmo comportamento IR, identidade comercial diferente;
- `full`: todas as capabilities declaradas no perfil funcionam;
- `partial`: apenas `scope` funciona;
- `family`: provável por pertencer à mesma família, sem cobertura completa;
- `unverified`: alegação ainda não testada;
- `incompatible`: evidência de que o perfil não deve ser usado.

`scope` é `all` ou uma lista de Capability IDs. `partial` DEVE usar lista. `full` e `exact` DEVERIAM usar `all`. Cada relação declara confiança, tipo de evidência, notas e data de teste.

Exemplo conceitual: `tv-samsung-au7700` pode declarar compatibilidade `full` com `tv-samsung-au8000` e `partial` com `tv-samsung-au9000`, limitada a power, volume e navegação. O catálogo do AU8000 deve declarar separadamente a relação inversa.

Compatibilidade NÃO DEVE ser inferida apenas por marca, aparência do controle ou proximidade do número do modelo.

## 12. Contribuição comunitária

Fluxo recomendado:

1. Criar Submission em estado `draft`.
2. Anexar ao menos uma evidência.
3. Declarar confiança e licença.
4. Atestar direitos e termos.
5. Alterar para `submitted`.
6. Realizar validação estrutural, revisão de licença e teste técnico.
7. Registrar revisores e decisão.
8. Se aceita, publicar uma nova versão do Device e manter a Submission imutável.

Captura e teste devem ser funções separáveis em `contributors.roles`. Para confiança alta, o revisor DEVERIA ser pessoa diferente do capturador.

Correções não devem apagar contribuições anteriores. Dados pessoais desnecessários, especialmente e-mail, NÃO DEVEM ser exigidos no documento público.

## 13. Versionamento

OpenIR possui duas camadas de versão.

### 13.1 Versão da especificação

A especificação usa Semantic Versioning:

- **major**: alteração incompatível de significado ou estrutura;
- **minor**: adição compatível de categorias, campos opcionais, enums ou capacidades;
- **patch**: esclarecimento sem mudança de dados válidos.

Documentos declaram apenas a linha major.minor em `openir_version`, por exemplo `1.0`. Correções 1.0.x não exigem alteração do documento.

Um consumidor v1:

- DEVE rejeitar major desconhecida;
- PODE aceitar minor posterior em modo tolerante;
- DEVE ignorar extensões `x-...` desconhecidas;
- NÃO DEVE reinterpretar valores desconhecidos como valores conhecidos.

### 13.2 Versão do registro

Cada Device usa SemVer independente em `version`:

- major: mudança incompatível do perfil, remoção ou redefinição de comando;
- minor: novos comandos, capabilities ou compatibilidades;
- patch: correções de texto, evidência ou precisão sem mudar intenção.

Versões publicadas são imutáveis. Deprecação cria nova versão. Alteração do aparelho identificado cria novo Device, não uma versão enganosa do antigo.

## 14. Perfis de distribuição

Para dispositivos com memória ou conectividade limitada, OpenIR define três projeções normativas do mesmo Device. Projeção remove campos; não muda seus valores.

### 14.1 `metadata`

Inclui:

- `openir_version`, `id`, `category`, `brand`, `model`, `aliases`;
- `description`, `year`, `region`, `manufacturer`;
- `capabilities`, `status`, `version`, `license`;
- resumo de compatibilidade, sem comandos.

Uso: busca, catálogo, seleção e avaliação antes do download.

### 14.2 `commands`

Inclui:

- `openir_version`, `id`, `version`;
- `commands`;
- definições de capabilities referenciadas;
- protocolo e parâmetros já incorporados em cada Command;
- licença mínima necessária à redistribuição.

Uso: atualização de comandos de um perfil já conhecido.

### 14.3 `full`

É o Device completo validado por `device.schema.json`. Uso: controle inteiro, arquivamento, edição e distribuição offline.

Manifestos, arquivos, pacotes ou transportes podem nomear o perfil, mas não fazem parte do Device. Um distribuidor DEVE associar a projeção ao `id`, `version`, `openir_version` e a um hash criptográfico do conteúdo. O mecanismo de download não é definido por OpenIR v1.

## 15. Extensões

Extensões experimentais de Device ficam em `extensions` e usam chaves `x-<organização>-<nome>`. Elas:

- não podem alterar o significado de campos normativos;
- devem ser opcionais;
- devem ser ignoráveis com segurança;
- não tornam um consumidor obrigado a implementá-las;
- devem possuir documentação pública para interoperabilidade.

Campos desconhecidos fora de `extensions` tornam o documento Device inválido em v1.

## 16. Integridade e segurança

Dados IR podem causar ações físicas. Consumidores DEVERIAM:

- limitar frequência, duração, repetição e tamanho de sequências;
- validar o documento antes de transmitir;
- exigir confirmação para ações potencialmente perigosas;
- não transmitir automaticamente Commands `future` desconhecidos;
- verificar hashes ao obter projeções ou evidências;
- tratar texto e URIs como dados não confiáveis.

Os limites estruturais dos schemas são máximos de interoperabilidade, não autorização para transmissão segura em qualquer hardware.

## 17. Conformidade

Um **documento Device conforme**:

1. valida contra `schemas/device.schema.json`;
2. satisfaz todas as regras semânticas desta especificação;
3. possui Capability correspondente a cada `Command.canonical_name`;
4. possui IDs únicos em `capabilities` e `commands`;
5. usa versão, licença, origem e confiança coerentes;
6. não depende de campos externos para interpretar os comandos incorporados.

Um **produtor conforme** gera documentos conformes e não descarta proveniência.

Um **consumidor conforme** valida a major, respeita `encoding_type`, repetição e frequência, ignora extensões permitidas e não afirma suporte ao que não consegue executar.

Uma **Submission conforme** valida contra `schemas/submission.schema.json`; aceitação editorial continua sendo decisão do projeto, não consequência automática da validação.

## 18. Registro de schemas

Os schemas normativos de OpenIR v1 são:

- `device.schema.json`
- `command.schema.json`
- `category.schema.json`
- `brand.schema.json`
- `protocol.schema.json`
- `capability.schema.json`
- `submission.schema.json`
- `compatibility.schema.json`

Todos usam JSON Schema Draft 2020-12 e IDs estáveis sob `https://openir.dev/schemas/v1/`.

## 19. Governança recomendada

A evolução do padrão deveria ocorrer por propostas públicas numeradas, com motivação, compatibilidade retroativa, exemplos, impacto em consumidores limitados e período de revisão.

IDs canônicos, categorias, capabilities e protocolos deveriam possuir registros mantidos publicamente. A inclusão no registro não implica implementação obrigatória. Alterações incompatíveis exigem uma nova major e período de coexistência.

Decisões de governança, hospedagem, API, banco de dados, parser e firmware estão deliberadamente fora do escopo da especificação v1.
