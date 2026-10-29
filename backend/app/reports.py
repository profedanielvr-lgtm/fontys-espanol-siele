"""Bilingual formative report; no conversion to an official SIELE score."""
from io import BytesIO
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def make_report(attempt):
    from .secure_exam import public
    out=BytesIO();styles=getSampleStyleSheet()
    styles['Title'].textColor=colors.HexColor('#183c47');styles['BodyText'].leading=15
    styles['Heading2'].keepWithNext=True
    p=lambda value:Paragraph(escape(str(value)).replace('\n','<br/>'),styles['BodyText'])
    story=[Paragraph('INFORME FORMATIVO<br/>FORMATIEF VERSLAG',styles['Title']),p('Práctica de español A1-C1 | Oefening Spaans A1-C1'),Spacer(1,12),p('Diseñado por / Ontworpen door Daniel Valle Robles'),p('Contexto: formación de profesores de español / lerarenopleiding Spaans - Fontys Hogeschool'),Spacer(1,12),p('Propuesta independiente. No es una certificación SIELE ni una acreditación de Fontys. / Onafhankelijk oefenmateriaal. Geen SIELE-certificaat of Fontys-accreditatie.'),Spacer(1,12),p('Identificador / Kenmerk: '+attempt.id),p('Fecha de emisión / Uitgiftedatum: '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')),p('Modalidad / Modaliteit: '+attempt.data['modality']),Spacer(1,15)]
    scores=public(attempt)['scores']
    rows=[[p('Destreza / Vaardigheid'),p('Resultado / Resultaat')]]
    for skill,label in [('lectura','Lectura / Lezen'),('escucha','Escucha / Luisteren')]:
        score=scores.get(skill)
        if score:rows.append([p(label),p(f"{score['correct']} / {score['total']} respuestas correctas / juiste antwoorden. Sin conversión MCER / Geen ERK-omrekening.")])
    for prefix,label in [('eie','Escritura / Schrijven'),('eio','Oral / Spreken')]:
        tasks=[t for t in attempt.data['task_ids'] if t.startswith(prefix)]
        if tasks:
            done=sum(attempt.data.get('reviews',{}).get(t,{}).get('estado')=='revisado_por_docente' for t in tasks)
            summary='Sin nota final / Geen eindscore.'
            if done==len(tasks):
                values=[v for t in tasks for v in attempt.data['reviews'][t]['revision_humana']['criterios'].values()]
                summary=f'Media descriptiva / Beschrijvend gemiddelde: {sum(values)/len(values):.2f}/4.'
            rows.append([p(label),p(f'{done}/{len(tasks)} tareas revisadas por docente / taken door docent beoordeeld. {summary} Bandas formativas propias 0-4, igual peso, sin equivalencia oficial / Eigen formatieve schalen 0-4, gelijk gewicht, zonder officiële equivalentie.')])
    table=Table(rows,colWidths=[135,350]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcece7')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#abc4c4')),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]));story.extend([table,Spacer(1,18)])
    for task in attempt.data['task_ids']:
        if not task.startswith(('eie','eio')):continue
        review=attempt.data.get('reviews',{}).get(task,{})
        human=review.get('revision_humana') if review.get('estado')=='revisado_por_docente' else None
        story.append(Paragraph(escape(task.upper())+' - '+('Revisión docente / Docentbeoordeling' if human else 'Pendiente de revisión / Wacht op beoordeling'),styles['Heading2']))
        if human:
            story.append(p('Docente / Docent: '+human['reviewer']))
            story.append(p(' | '.join(f'{k}: {v}/4' for k,v in human['criterios'].items())))
            story.append(p('Nivel estimado / Geschat niveau: '+(human.get('nivel_estimado') or 'No determinado / Niet vastgesteld')))
            story.extend([p(human['observaciones_es']),p(human['observaciones_nl'])])
        else:story.append(p('Sin calificación final. Las propuestas de IA requieren validación humana. / Geen eindbeoordeling. AI-voorstellen vereisen menselijke controle.'))
        story.append(Spacer(1,10))
    story.extend([Paragraph('Base y límites / Grondslag en beperkingen',styles['Heading2']),p('Descriptores de referencia: MCER, Volumen complementario 2020. Criterios y bandas de esta plataforma son propios; no son rúbricas oficiales SIELE. / Referentie: ERK, Companion Volume 2020. De criteria en schalen van dit platform zijn eigen schalen, geen officiële SIELE-rubrics.'),p('La transcripción automática no permite por sí sola valorar pronunciación ni fluidez. / Een automatische transcriptie volstaat niet om uitspraak of vloeiendheid te beoordelen.'),p('Fuente / Bron: https://www.coe.int/en/web/common-european-framework-reference-languages')])
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.drawString(55,30,'Daniel Valle Robles | Informe formativo / Formatief verslag');canvas.drawRightString(540,30,str(doc.page))
    SimpleDocTemplate(out,pagesize=(595.28,841.89),rightMargin=55,leftMargin=55,topMargin=45,bottomMargin=50,title='Informe formativo - Fontys Español',author='Daniel Valle Robles').build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
