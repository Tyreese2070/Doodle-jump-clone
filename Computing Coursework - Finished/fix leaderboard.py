import pickle
from operator import itemgetter

def leaderboard_append(username, score, leaderboard_list):
    leaderboard_list.append((username, score))
    file = open("leaderboard.txt", "wb")
    leaderboard_list = sorted(leaderboard_list, key = itemgetter(1), reverse = True)
    pickle.dump(leaderboard_list, file)
    file.close
    

def save_leaderboard(leaderboard_list):
    file = open("leaderboard.txt", "wb")
    pickle.dump(sorted(leaderboard_list, key = itemgetter(1), reverse = True), file)
    file.close

def load_leaderboard():
    file = open("leaderboard.txt", "rb")
    leaderboard_list = sorted(pickle.load(file), key = itemgetter(1), reverse = True)
    file.close
    return leaderboard_list

leaderboard = [("a",0), ("b",0), ("c",0), ("d",0), ("e",0), ("f",0), ("g",0), ("h",0), ("i",0), ("j",0)]

save_leaderboard(leaderboard)
print(load_leaderboard())
