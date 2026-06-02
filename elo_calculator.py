def calcular_expectativa(mmr_jogador, mmr_oponente):
    """
    Calcula a probabilidade (expectativa de vitória) de um jogador contra outro.
    A fórmula padrão do Elo é: 1 / (1 + 10 ** ((mmr_oponente - mmr_jogador) / 400))
    """
    return 1 / (1 + 10 ** ((mmr_oponente - mmr_jogador) / 400))

def calcular_novo_mmr(mmr_atual, expectativa, resultado, k=32):
    """
    Calcula o novo MMR do jogador após a partida.
    - mmr_atual: MMR antes da partida.
    - expectativa: probabilidade de vitória calculada.
    - resultado: 1 para vitória, 0 para derrota, 0.5 para empate.
    - k: Fator de volatilidade (por padrão 32, usado pela FIDE para novos jogadores/jogadores de clube).
    """
    # A fórmula é: MMR + K * (Resultado - Expectativa)
    novo_mmr = mmr_atual + k * (resultado - expectativa)
    return round(novo_mmr)
