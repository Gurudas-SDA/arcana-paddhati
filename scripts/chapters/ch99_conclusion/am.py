import configparser, requests, sys
c = configparser.ConfigParser(); c.read('/home/satkirti/.config/anymodel.ini', encoding='utf-8')
KEY = c['anymodel']['api_key']
def chat(prompt, system=None, model='cx/gpt-6.1-sol', timeout=900):
    msgs = ([{'role': 'system', 'content': system}] if system else []) + [{'role': 'user', 'content': prompt}]
    last = None
    for m in (model, model, 'cx/gpt-6-sol'):  # CLAUDE.md §5: primary twice, then alt cx/gpt-6-sol
        try:
            r = requests.post('https://anymodel.org/v1/chat/completions', headers={'Authorization': 'Bearer ' + KEY},
                              json={'model': m, 'messages': msgs}, timeout=timeout)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content'], m
            last = (m, r.status_code, r.text[:200])
        except Exception as e:
            last = (m, str(e)[:200])
    raise RuntimeError(f'AnyModel failed: {last}')
if __name__ == '__main__':
    print(chat('Translate to English: «Заключение»'))
