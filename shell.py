import Hinglish
while True:
    text = input('Hinglish > ')
    result, error = Hinglish.run('<stdin>', text)
    if error:
        print(error.as_string())
    else:
        print(result)
