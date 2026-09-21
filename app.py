from server import app

if __name__ == "__main__":
    from server import PORT
    app.run(host="0.0.0.0", port=PORT)
