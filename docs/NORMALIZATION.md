# Normalização e classificação OpenIR

## Objetivo

A ferramenta em `tools/normalization/` lê relatórios produzidos pelo inventário IR e gera propostas auditáveis para revisão humana. Ela não converte, move, corrige ou publica sinais.

Uso:

```text
python -m tools.normalization analyze --inventory reports --output normalization
python -m tools.normalization inspect <caminho-ou-id>
```

`analyze` procura automaticamente os relatórios conhecidos, incluindo `inventory.json`, `inventory.csv`, `categories.json`, `brands.json`, `commands.json`, `protocols.json`, `duplicates.json`, `raw-analysis.json` e `parse-errors.json`.

Se nenhum relatório existir, todos os arquivos de saída ainda são gerados, vazios e com advertência explícita. Nenhum dado é inventado.

## Limites

A fase produz somente sugestões. Ela:

- não cria Device, Binding ou Signal OpenIR;
- não altera arquivos `.ir`;
- não infere licença;
- não pesquisa web;
- não usa IA, API ou aleatoriedade;
- não aplica silenciosamente valores ambíguos;
- não substitui o valor original.

O formato dos relatórios de inventário pode variar. O leitor reconhece chaves usuais e preserva o objeto original no modelo interno. Formatos novos devem ganhar fixture e regra explícita.

## Saídas

JSON:

- `category-map.proposed.json`;
- `brand-map.proposed.json`;
- `command-aliases.proposed.json`;
- `model-candidates.json`;
- `file-classification.json`;
- `conflicts.json`;
- `review-queue.json`.

CSV:

- `file-classification.csv`;
- `brand-map.csv`;
- `model-candidates.csv`;
- `command-aliases.csv`;
- `review-queue.csv`.

`normalization-summary.md` contém contagens determinísticas e advertências da execução.

## Classificação de arquivos

Classes:

- `specific_device`;
- `device_family`;
- `universal_remote`;
- `brute_force`;
- `mixed_collection`;
- `test_or_sample`;
- `malformed`;
- `unknown`.

A decisão combina caminho, modelo detectável, quantidade de sinais, comandos numerados, repetição de intenções, diversidade de protocolos, diversidade de endereços e erros de parsing.

O caminho nunca decide sozinho. Por exemplo, `Universal/` fornece evidência inicial, mas é necessário um conjunto amplo, numerado ou tecnicamente diverso para confirmar `universal_remote`.

Arquivos podem carregar conflitos com classificações alternativas. Resultados abaixo de 0,80 ou conflitantes entram na fila de revisão.

## Bruteforce

Evidências incluem:

- `Power1`, `Power2`, `Power3` e outras sequências;
- muitos comandos com a mesma base;
- 64 ou mais sinais;
- vários protocolos;
- muitos endereços;
- ausência de modelo;
- `brute` ou `codeset` no caminho.

Cada contribuição de regra é fixa. A confiança final não usa números aleatórios.

## Categorias

A taxonomia proposta inclui:

`tv`, `air_conditioner`, `fan`, `projector`, `receiver`, `soundbar`, `led_strip`, `camera`, `light`, `media_player`, `set_top_box`, `dvd_player`, `blu_ray_player`, `game_console`, `heater`, `humidifier`, `air_purifier`, `other` e `unknown`.

Aliases explícitos, como `Televisions` → `tv`, recebem confiança alta. Evidência somente de caminho recebe confiança menor e revisão. Múltiplas categorias detectadas resultam em `null`.

Para adicionar categoria ou alias, edite `CATEGORY_ALIASES` em `categories.py`, acrescente testes e documente qualquer ambiguidade.

## Marcas

A regra segura normaliza Unicode, caixa, espaços e pontuação para sugerir `brand_id`. A grafia original é sempre preservada.

Valores genéricos como `Generic`, `Unknown`, `Universal` e `Misc` não viram marcas. A ferramenta não usa distância textual para fundir marcas parecidas e não separa fabricante de marca sem evidência explícita.

Para adicionar um alias comprovado, a futura regra deve ser versionada, possuir evidência local e teste. Pesquisa externa não faz parte desta fase.

## Modelos

Ordem de evidência:

1. campo explícito do inventário;
2. nome do arquivo;
3. diretório pai;
4. comentários.

Um candidato extraído precisa conter letras e números. Termos genéricos são excluídos. Mais de um candidato gera alternativas e revisão. Sem candidato claro, `candidate` é `null`.

## Comandos

Aliases ficam em `commands.py`. A normalização é NFKC, case-insensitive e conserva `+`/`-`.

Aliases exatos como `Volume+` → `volume_up` têm alta confiança. Termos contextuais, como `Up`, e nomes numerados, como `Power1`, recebem confiança menor e revisão. Nomes não reconhecidos produzem `canonical_name: null`.

Para adicionar alias:

1. confirme que o significado é independente de fabricante;
2. acrescente a grafia ao mapa explícito;
3. adicione teste positivo;
4. adicione teste de colisão quando o termo também puder ter outro sentido.

## Confiança

- 0,95–1,00: praticamente determinístico;
- 0,80–0,94: evidência forte;
- 0,60–0,79: provável;
- 0,40–0,59: ambíguo;
- abaixo de 0,40: não aplicar automaticamente.

Toda proposta possui razões e evidências. Confiança não é probabilidade estatística.

## Revisão humana

Entram na fila:

- categoria, marca ou modelo ausente/ambíguo;
- comando desconhecido ou contextual;
- classificação conflitante ou abaixo do limiar;
- múltiplos candidatos de modelo.

A fila não altera a origem. Uma decisão humana futura deve registrar revisor, decisão, justificativa e versão da regra.

## Determinismo

Todas as chaves JSON, linhas CSV e listas de registros são ordenadas. Não há timestamp nas saídas. Duas execuções sobre os mesmos bytes de entrada devem produzir arquivos idênticos.

## Por que não há conversão

Classificação e conversão possuem riscos diferentes. Normalização incorreta pode associar um sinal ao aparelho errado ou apagar contexto de licença e origem. Nesta fase, as sugestões permanecem separadas do acervo para que regras e ambiguidades sejam revisadas antes de qualquer transformação.
