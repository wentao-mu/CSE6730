def log_match_state(mstate):
    minutes = mstate.time % 60
    seconds = mstate.time - 60*minutes
    possession = mstate.possession + 1 # 0 -> team 1, 1 -> team 2
    print(f"Time:\n{minutes}:{seconds}")
    print("Score:\n", mstate.score)
    print(f"Posession:\nTeam {possession}\n")
    