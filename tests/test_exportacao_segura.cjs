const {test}=require('node:test'),assert=require('node:assert/strict');
const csv=require('../exportacao-segura.js');
for(const valor of ['=SUM(1;2)','+1','-2','@A1',' \t=1','\uFEFF=1','＝1','\ntexto'])test('neutraliza '+JSON.stringify(valor),()=>assert.equal(csv.valor(valor),"'"+valor));
test('mantém aspas, separador, quebra e zero',()=>{
 assert.equal(csv.linha(['A;B','C"D','duas\nlinhas',0,null]),'"A;B";"C""D";"duas\nlinhas";"0";""\r\n');
});
