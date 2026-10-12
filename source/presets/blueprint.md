<!-- blueprint.md | Atualizado pela Spec 5.2 -->

# Blueprint Visual e Frontend

Este preset força a criação de uma especificação focada em UI/UX e desenvolvimento frontend rigoroso. Ele implementa o princípio do **Standalone Blueprint**, impedindo hand-offs deficientes e garantindo que o escopo contenha todas as informações necessárias para recriar o estado atual da interface a partir do zero.

## Seções Obrigatórias:

1. **Visão Global:** Descrição clara da stack, bibliotecas externas utilizadas e objetivo da ferramenta.
2. **Design System:** Valores literais de cores (`:root` e hexadecimais literais), tipografia, e padrões de UI (ex: glassmorphism, sombras).
3. **Catálogo de Componentes Visuais e Comportamentais:** Toda animação e estado interativo deve ter seus parâmetros CSS/JS exatos documentados na SPEC (durações, keyframes, easings, parâmetros de áudio nativo).
4. **Comportamento Interativo e Scripts Externos:** Descrever detalhadamente objetos de inicialização complexos (como config de canvas, webgl, swipers, e bibliotecas de drag).
5. **Contratos de API:** Documentar a resposta esperada dos endpoints e as rotas definidas.
6. **Plano de Testes (TDD):** Nomes de testes que devem ser escritos antes de iniciar a implementação do código.
