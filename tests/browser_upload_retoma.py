import unittest
import browser_text_safety as safety

class Retoma(safety.TextSafetyBrowser):
    def test_interrupcao_individual_retomada_e_fotos_concluidas_preservadas(self):
        self.open();self.page.add_style_tag(content=".hidden{display:none!important}#loadingOverlay{display:none!important}")
        self.page.evaluate('''()=>{
            document.getElementById('loginAlunoScreen').classList.add('hidden');
            const box=document.createElement('div');box.id='testeUploads';document.body.append(box);
            window.testManager=new UploadFotos('testeUploads',()=> 'token');
            window.servidor=new Map();window.envios=[];let prox=0;let falhar=true;
            window.fetch=async(url,opts={})=>{
                const path=new URL(url).pathname;
                const resposta=(data,ok=true,status=200)=>({ok,status,json:async()=>data});
                if(path==='/api/uploads'){
                    const id=String(++prox);const meta=JSON.parse(opts.body);servidor.set(id,{id,recebidos:0,total:meta.tamanho});return resposta({id},true,201);
                }
                const id=path.split('/')[3],arq=servidor.get(id);
                if(opts.method==='PUT'||path.endsWith('/parte')){
                    const offset=Number(opts.headers['X-Upload-Offset']);envios.push([id,offset]);
                    if(id==='1'&&offset===65536&&falhar){falhar=false;throw Error('rede indisponível');}
                    arq.recebidos=offset+opts.body.size;return resposta({recebidos:arq.recebidos});
                }
                if(path.endsWith('/finalizar')){arq.url='https://foto.invalid/'+id;return resposta({url:arq.url});}
                return resposta(arq);
            };
            window.fotosTeste=[1,2].map(n=>'data:image/jpeg;base64,'+btoa(String.fromCharCode(n).repeat(150000)));
            window.primeira=testManager.enviarTodas(fotosTeste).catch(e=>e.message);
        }''')
        self.page.evaluate('window.primeira')
        states=self.page.locator('#testeUploads [role="status"]').all_text_contents()
        self.assertIn('interrompido',states[0]);self.assertIn('Enviada',states[1])
        self.page.evaluate('window.antes=envios.length')
        self.page.locator('#testeUploads button').first.click()
        self.page.wait_for_function('testManager.arquivos.get(fotosTeste[0]).url!==null')
        novos=self.page.evaluate('envios.slice(antes)')
        self.assertEqual(novos[0],['1',65536]);self.assertTrue(all(x[0]=='1' for x in novos))
        self.page.evaluate('testManager.enviarTodas(fotosTeste)')
        self.assertEqual(self.page.evaluate('envios.length'),self.page.evaluate('antes')+len(novos))

def load_tests(loader,tests,pattern):return unittest.TestSuite([Retoma('test_interrupcao_individual_retomada_e_fotos_concluidas_preservadas')])
if __name__=='__main__':unittest.main(verbosity=2)
