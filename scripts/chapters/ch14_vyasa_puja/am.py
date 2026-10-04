import configparser,requests,json,sys,time
c=configparser.ConfigParser(); c.read(r'C:\Users\gurud\.credentials\ca_pipeline\config.ini',encoding='utf-8')
KEYS=[c['anymodel'][f'key_{i}'] for i in (10,9,8,7,6) if f'key_{i}' in c['anymodel']]
def chat(prompt, system=None, model='cx/gpt-6.1-sol', timeout=600):
    msgs=([{'role':'system','content':system}] if system else [])+[{'role':'user','content':prompt}]
    last=None
    for m in (model,'cx/gpt-6-sol'):
        for k in KEYS:
            try:
                r=requests.post('https://anymodel.org/v1/chat/completions',headers={'Authorization':'Bearer '+k},json={'model':m,'messages':msgs},timeout=timeout)
                if r.status_code==200:
                    j=r.json(); return j['choices'][0]['message']['content'], m
                last=(m,r.status_code,r.text[:200])
            except Exception as e: last=(m,str(e)[:200])
    raise RuntimeError(f'AnyModel failed: {last}')
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(chat('Translate to English: «Праздники и обеты»'))
