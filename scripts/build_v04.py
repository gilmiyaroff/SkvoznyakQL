#!/usr/bin/env python3
"""Build SKVOZNYAK v0.4 private and public-safe standalone HTML artifacts."""
from __future__ import annotations
import argparse,csv,json,re
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
import openpyxl

META_FILES=[f"meta_ads_daily_2026-{m}.csv" for m in ('04','05','06','07','08','09')]+['meta_ads_daily_2026-10_partial.csv']
def find(root,name):
 p=list(root.rglob(name))+list(root.rglob(name+'.bin'))
 if not p: raise FileNotFoundError(name)
 return p[0]
def s(v): return str(v or '').strip()
def n(v):
 try:return float(str(v or 0).replace('\xa0','').replace(' ','').replace(',','.'))
 except:return 0.0
def date(v):
 if not v:return ''
 if isinstance(v,datetime):return v.date().isoformat()
 t=s(v)
 for f in ('%Y-%m-%d','%d.%m.%Y %H:%M:%S','%d.%m.%Y'):
  try:return datetime.strptime(t[:19],f).date().isoformat()
  except:pass
 return t[:10] if re.fullmatch(r'\d{4}-\d{2}-\d{2}.*',t) else ''
def yes(v): return s(v).lower() in {'да','yes','true','1','оплачено','полностью оплачено'}
def safe_url(u):
 u=s(u)
 if not u:return ''
 try:q=urlsplit(u)
 except:return ''
 host=q.netloc.lower().removeprefix('www.')
 if q.scheme!='https' or q.query or q.fragment:return ''
 if host=='instagram.com' and re.match(r'^/(p|reel|tv)/[A-Za-z0-9_-]+/?$',q.path):return u
 if host=='fb.me' and re.match(r'^/[A-Za-z0-9_-]+/?$',q.path):return u
 return ''
def canonical(counter):
 safe=Counter({u:c for u,c in counter.items() if safe_url(u)})
 if not safe:return '',[],False
 ordered=sorted(safe,key=lambda u:(-safe[u],u));return ordered[0],ordered[1:],len(ordered)>1
def redact_public_text(value):
 value=re.sub(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b','[email скрыт]',s(value),flags=re.I)
 value=re.sub(r'(?<!\d)(?:\+?7|8)[\s()\-]*\d{3}[\s()\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)','[телефон скрыт]',value)
 return value
def load_meta(root,fx):
 rows=[];ads={};files=[];seen=set()
 for name in META_FILES:
  p=find(root,name)
  with p.open(encoding='utf-8-sig',newline='') as f:
   rr=csv.DictReader(f);count=0;spend=0
   for r in rr:
    ad=s(r.get('ID рекламы'))
    if not re.fullmatch(r'\d{18}',ad):raise ValueError(f'Invalid Ad ID {ad!r} in {name}')
    d=date(r.get('Дата начала отчетности')); account=s(r.get('Идентификатор аккаунта'))
    key=(account,ad,d)
    if key in seen:raise ValueError(f'Duplicate {key}')
    seen.add(key);count+=1
    usd=n(r.get('Потраченная сумма (USD)'));spend+=usd
    x={
     'd':d,'id':ad,'usd':usd,'kzt':round(usd*fx[d],4),'imp':n(r.get('Показы')),'reach':n(r.get('Охват')),
     'allc':n(r.get('Клики (все)')),'linkc':n(r.get('Клики по ссылке')),'res':n(r.get('Результат')),
     'rtype':s(r.get('Индикатор результата')),'startmsg':n(r.get('Начата переписка')),
     'contacts':n(r.get('Всего контактов по переписке')),'newcontacts':n(r.get('Новые контакты по переписке')),
     'metaleads':n(r.get('Лиды'))
    };rows.append(x)
    a=ads.setdefault(ad,{'id':ad,'name':s(r.get('Название объявления')),'campaign':s(r.get('Название кампании')),'campaign_id':s(r.get('Идентификатор кампании')),'adset':s(r.get('Название группы объявлений')),'adset_id':s(r.get('ID группы объявлений')),'account_id':account,'status':s(r.get('Показ рекламы')) or 'Unknown','created':date(r.get('Дата создания')),'scheduled_start':date(r.get('Начало')),'scheduled_end':date(r.get('Конец')),'last_edit':date(r.get('Дата последнего редактирования')),'mechanism':'Unknown','dates':[],'spend_dates':[],'result_types':Counter()})
    a['dates'].append(d)
    if usd>0:a['spend_dates'].append(d)
    if x['rtype']:a['result_types'][x['rtype']]+=1
    tags=s(r.get('url_tags')).lower();camp=a['campaign'].lower()
    if 'lead_form' in tags or 'lead_form' in camp:a['mechanism']='Lead Form'
    elif 'insta' in tags or 'direct' in tags or 'insta' in camp:a['mechanism']='Instagram Direct'
    elif 'whatsapp' in tags or 'whatsapp' in camp or 'wp_' in tags:a['mechanism']='WhatsApp'
   files.append({'file':name,'rows':count,'spend_usd':round(spend,2)})
 for a in ads.values():
  a['first_activity']=min(a['dates']);a['last_activity']=max(a['dates']);a['first_spend']=min(a['spend_dates']) if a['spend_dates'] else ''
  a['last_spend']=max(a['spend_dates']) if a['spend_dates'] else '';a['spend_days']=len(set(a['spend_dates']))
  a['observed_days']=(datetime.fromisoformat(a['last_activity'])-datetime.fromisoformat(a['first_activity'])).days+1
  a['result_type']=a['result_types'].most_common(1)[0][0] if a['result_types'] else ''
  del a['dates'],a['spend_dates'],a['result_types']
 return rows,ads,files
def load_crm(path,ads,public_k=5):
 ws=openpyxl.load_workbook(path,read_only=True,data_only=True).active;it=ws.iter_rows(values_only=True)
 h=[s(x) for x in next(it)];ix={x:i for i,x in enumerate(h)}
 def g(row,k):return row[ix[k]] if k in ix and ix[k]<len(row) else None
 deals=[];links=defaultdict(Counter);heads=defaultdict(Counter);texts=defaultdict(Counter);ids=set();dups=0
 for row in it:
  did=s(g(row,'ID'))
  if not did:continue
  if did in ids:dups+=1;continue
  ids.add(did);ad=s(g(row,'FB ad id'));ctwa=bool(s(g(row,'FB CTWA')));qraw=s(g(row,'Квалифицированный')).lower()
  qual='yes' if qraw=='да' else 'no' if qraw=='нет' else 'unknown'
  amount=n(g(row,'Сумма оплаты, тг'));pre=n(g(row,'Сумма предоплаты, тг'));full_date=date(g(row,'Дата полной оплаты'));pre_date=date(g(row,'Дата предоплаты'));full=yes(g(row,'Полная сумма оплачена'))
  if amount>0 and (full or full_date):sale='full';revenue=amount;paydate=full_date
  elif pre>0 and pre_date:sale='partial';revenue=pre;paydate=pre_date
  elif amount>0 or pre>0 or full or full_date or pre_date:sale='possible';revenue=0;paydate=''
  else:sale='unpaid';revenue=0;paydate=''
  created=date(g(row,'Дата создания'));attr='ctwa' if ad in ads and ctwa else 'ad_only' if ad in ads else 'unmatched'
  deal={'deal_id':did,'ad_id':ad,'created':created,'qualified':qual,'urgency':s(g(row,'Квалифицирован')),'sale':sale,'revenue':revenue,'payment_date':paydate,'pipeline':s(g(row,'Воронка')),'stage':s(g(row,'Этап сделки')),'manager':s(g(row,'Ответственный')),'attr':attr}
  deals.append(deal)
  if ad:
   u=s(g(row,'FB URL'));he=s(g(row,'FB Headline'));tx=s(g(row,'FB Text'))
   if u:links[ad][u]+=1
   if he:heads[ad][he]+=1
   if tx:texts[ad][tx]+=1
 for ad,a in ads.items():
  u,alts,amb=canonical(links[ad]);a['creative_url']=u;a['creative_alternatives']=alts;a['creative_ambiguous']=amb
  a['headline']=heads[ad].most_common(1)[0][0] if heads[ad] else '';a['text']=texts[ad].most_common(1)[0][0] if texts[ad] else ''
  a['creative_url_count']=len([x for x in links[ad] if safe_url(x)]);a['unsafe_url_count']=len(links[ad])-a['creative_url_count']
  a['meta_url']=f"https://www.facebook.com/adsmanager/manage/ads/edit?act={a['account_id']}&selected_ad_ids={ad}" if a['account_id'] else ''
 audit={'rows':len(deals),'duplicates':dups,'with_ad_id':sum(bool(d['ad_id']) for d in deals),'exact':sum(d['attr']!='unmatched' for d in deals),'ctwa':sum(d['attr']=='ctwa' for d in deals),'ad_only':sum(d['attr']=='ad_only' for d in deals),'unmatched':sum(d['attr']=='unmatched' for d in deals),'unknown_qualification':sum(d['qualified']=='unknown' for d in deals),'creative_ok':sum(bool(a['creative_url']) for a in ads.values()),'creative_missing':sum(not a['creative_url'] for a in ads.values()),'creative_ambiguous':sum(a['creative_ambiguous'] for a in ads.values())}
 return deals,audit
def make_payload(meta,ads,deals,fx,files,audit,private,k):
 adlist=list(ads.values());idx={a['id']:i for i,a in enumerate(adlist)}
 m=[[r['d'],idx[r['id']],r['usd'],r['kzt'],r['imp'],r['reach'],r['allc'],r['linkc'],r['res'],r['rtype'],r['startmsg'],r['contacts'],r['newcontacts'],r['metaleads']] for r in meta]
 leads=defaultdict(lambda:[0,0,0,0,0]);sales=defaultdict(lambda:[0,0,0,0]);private_deals=[]
 for d in deals:
  if d['ad_id'] not in idx:continue
  ai=idx[d['ad_id']];key=(d['created'],ai);z=leads[key];z[0]+=1;z[1]+=d['attr']=='ctwa';z[2]+=d['attr']=='ad_only';z[3]+=d['qualified']=='yes';z[4]+=d['qualified']=='no'
  if d['sale'] in {'full','partial'} and d['payment_date']:
   p=sales[(d['payment_date'],ai)];p[0]+=1;p[1]+=d['sale']=='full';p[2]+=d['sale']=='partial';p[3]+=d['revenue']
  if private:private_deals.append(d)
 l=[[d,i,*v] for (d,i),v in sorted(leads.items()) if d]
 if private:
  p=[[d,i,*v] for (d,i),v in sorted(sales.items())];pr=[]
 else:
  # Public data contains sale counts but no individual/small-cell revenue. Revenue is available only
  # in complete ad-month cells with k+ paid deals and is rounded to 10,000 KZT.
  monthly=defaultdict(lambda:[0,0,0,0])
  for (d,i),v in sales.items():
   z=monthly[(d[:7],i)]
   for j in range(4):z[j]+=v[j]
  p=[[d,i,v[0],v[1],v[2],None] for (d,i),v in sorted(sales.items())]
  pr=[[month,i,v[0],round(v[3]/10000)*10000 if v[0]>=k else None] for (month,i),v in sorted(monthly.items())]
 for a in adlist:
  if not private:
   a.pop('creative_alternatives',None)
   a['headline']=redact_public_text(a.get('headline'))
   a['text']=redact_public_text(a.get('text'))
 payload={'version':'0.4','private':private,'k':k,'date_min':min(r['d'] for r in meta),'date_max':max(r['d'] for r in meta),'ads':adlist,'m':m,'l':l,'p':p,'pr':pr,'deals':private_deals,'fx':fx,'audit':{'meta_rows':len(meta),'ads':len(adlist),'files':files,**audit},'schema':{'m':['date','ad','spend_usd','spend_kzt','impressions','daily_reach','all_clicks','link_clicks','results','result_type','messages_started','contacts','new_contacts','meta_leads'],'l':['created_date','ad','leads','ctwa','ad_only','qualified','not_qualified'],'p':['payment_date','ad','sales','full','partial','revenue_kzt'],'pr':['month','ad','sales_in_cell','suppressed_or_rounded_revenue_kzt']}}
 return payload
def render(template,payload,out):
 raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</script>','<\\/script>')
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(template.read_text(encoding='utf-8').replace('__DATA__',raw),encoding='utf-8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--input-root',type=Path,required=True);p.add_argument('--fx-json',type=Path,required=True);p.add_argument('--template',type=Path,default=Path(__file__).parents[1]/'src'/'v04.template.html');p.add_argument('--public-out',type=Path,required=True);p.add_argument('--public-mirror',type=Path);p.add_argument('--private-out',type=Path);p.add_argument('--public-k',type=int,default=5);a=p.parse_args()
 fxj=json.loads(a.fx_json.read_text());fx={x['date']:x['usd_kzt'] for x in fxj['rows']};meta,ads,files=load_meta(a.input_root,fx);deals,audit=load_crm(find(a.input_root,'amocrm_deals_export_2026-10-12.xlsx'),ads,a.public_k)
 public_payload=make_payload(meta,ads,deals,fx,files,audit,False,a.public_k);render(a.template,public_payload,a.public_out)
 if a.public_mirror:render(a.template,public_payload,a.public_mirror)
 if a.private_out:render(a.template,make_payload(meta,ads,deals,fx,files,audit,True,a.public_k),a.private_out)
 print(json.dumps({'meta':len(meta),'ads':len(ads),'deals':len(deals),'exact':audit['exact'],'ctwa':audit['ctwa'],'creative_ok':audit['creative_ok'],'creative_missing':audit['creative_missing'],'creative_ambiguous':audit['creative_ambiguous'],'public':str(a.public_out),'private':str(a.private_out or '')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
