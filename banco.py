import sqlite3

def conectar():
    return sqlite3.connect("Sistema-agendamento.db")

conn = conectar()

