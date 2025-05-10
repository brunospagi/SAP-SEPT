from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Item, Movimentacao, Responsavel
from django.db import transaction, models
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
import csv
import logging
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer
logger = logging.getLogger(__name__)

@login_required
def importar_csv(request):
    if request.method == 'POST':
        if not request.FILES.get('arquivo'):
            messages.error(request, "Nenhum arquivo selecionado!")
            return redirect('importar_csv')
            
        try:
            arquivo = request.FILES['arquivo'].read().decode('latin-1').splitlines()
            leitor = csv.DictReader(arquivo, delimiter=';')
            
            contador = 0
            with transaction.atomic():
                for linha in leitor:
                    logger.debug(f"Processando linha: {linha}")
                    
                    responsavel_partes = linha.get('Responsável', '').split(' - ', 1)
                    if len(responsavel_partes) != 2:
                        raise ValueError(f"Formato inválido do responsável: {linha['Responsável']}")
                        
                    responsavel, _ = Responsavel.objects.get_or_create(
                        codigo=responsavel_partes[0].strip(),
                        defaults={'nome': responsavel_partes[1].strip()}
                    )
                    
                    Item.objects.update_or_create(
                        tombo=linha['Tombo'],
                        defaults={
                            'descricao': linha.get('Descrição', ''),
                            'caracteristicas': linha.get('Característica', ''),
                            'local_oficial': linha.get('Local oficial', ''),
                            'local_atual': '',
                            'status': 'nao_localizado',
                            'responsavel': responsavel
                        }
                    )
                    contador += 1
                    
            messages.success(request, f"Importação concluída! {contador} itens processados")
            return redirect('dashboard')
            
        except Exception as e:
            logger.error(f"Erro na importação: {str(e)}", exc_info=True)
            messages.error(request, f"Falha na importação: {str(e)}")
            return redirect('importar_csv')
    
    return render(request, 'importar_csv.html')

@login_required
def dashboard(request):
    item_buscado = None
    movimentacoes = []
    tombo_busca = request.GET.get('tombo_busca')

    if tombo_busca:
        try:
            item_buscado = Item.objects.get(tombo=tombo_busca)
            movimentacoes = Movimentacao.objects.filter(item=item_buscado).order_by('-data')
        except Item.DoesNotExist:
            messages.error(request, "Tombo não encontrado!")

    # Novas métricas
    total_geral = Item.objects.count()
    nao_escaneados = Item.objects.filter(local_atual='').count()
    localizados_count = Item.objects.filter(local_atual=models.F('local_oficial')).count()
    
    try:
        porcentagem_localizados = round((localizados_count / total_geral) * 100, 2)
    except ZeroDivisionError:
        porcentagem_localizados = 0.0

    locais = []
    for local_oficial in Item.objects.values('local_oficial').distinct():
        loc = local_oficial['local_oficial']
        
        localizados = Item.objects.filter(local_oficial=loc, local_atual=loc)
        nao_localizados = Item.objects.filter(local_oficial=loc).exclude(local_atual=loc)
        transferidos = Item.objects.filter(local_atual=loc).exclude(local_oficial=loc)
        total_local = localizados.count() + nao_localizados.count()
        
        try:
            porcentagem_local = round((localizados.count() / total_local) * 100, 2)
        except ZeroDivisionError:
            porcentagem_local = 0.0

        locais.append({
            'nome': loc,
            'localizados': localizados,
            'nao_localizados': nao_localizados,
            'transferidos': transferidos,
            'total': total_local,
            'porcentagem_localizado': porcentagem_local
        })

    context = {
        'total_geral': total_geral,
        'nao_escaneados': nao_escaneados,
        'localizados_count': localizados_count,
        'porcentagem_localizados': porcentagem_localizados,
        'locais': locais,
        'item_buscado': item_buscado,
        'movimentacoes': movimentacoes
    }
    return render(request, 'dashboard.html', context)

@login_required
def scan_codigo(request):
    if request.method == 'POST':
        tombo = request.POST.get('tombo')
        novo_local = request.POST.get('novo_local')
        confirmed = request.POST.get('confirmed', 'false')
        precheck = request.POST.get('precheck', 'false')

        try:
            item = Item.objects.get(tombo=tombo)
            
            # Modo de pré-verificação
            if precheck == 'true':
                if novo_local != item.local_oficial:
                    return JsonResponse({
                        'status': 'confirmation_required',
                        'message': 'Você está movendo para fora do local oficial!',
                        'local_oficial': item.local_oficial
                    })
                return JsonResponse({'status': 'ok'})

            # Processar movimentação
            if novo_local != item.local_atual:
                if novo_local != item.local_oficial and confirmed != 'true':
                    return JsonResponse({
                        'status': 'confirmation_required',
                        'message': 'Confirmar movimentação para local diferente do oficial?',
                        'local_oficial': item.local_oficial
                    })

                Movimentacao.objects.create(
                    item=item,
                    local_anterior=item.local_atual,
                    novo_local=novo_local,
                    responsavel=request.user
                )
                item.local_atual = novo_local
                item.status = 'localizado'
                item.save()

            return JsonResponse({
                'status': 'success',
                'descricao': item.descricao
            })
            
        except Item.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item não encontrado'}, status=404)
    
    return render(request, 'scan.html')

@login_required
def relatorio_movimentacoes(request):
     # Filtros
    local = request.GET.get('local', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    movimentacoes = Movimentacao.objects.all().order_by('-data')
    
    if local:
        movimentacoes = movimentacoes.filter(
            models.Q(local_anterior=local) | 
            models.Q(novo_local=local)
        )
        
    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
        
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)
    
     # Obter lista de locais
    novos_locais = Movimentacao.objects.values_list('novo_local', flat=True).distinct()
    locais_anteriores = Movimentacao.objects.values_list('local_anterior', flat=True).distinct()
    locais = sorted(list(set(novos_locais.union(locais_anteriores))))

    # Export CSV
    if 'exportar' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="movimentacoes.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Data', 'Tombo', 'Descrição', 'Local Anterior', 'Novo Local', 'Responsável'])
        
        for mov in movimentacoes:
            writer.writerow([
                mov.data.strftime("%d/%m/%Y %H:%M"),
                mov.item.tombo,
                mov.item.descricao,
                mov.local_anterior,
                mov.novo_local,
                mov.responsavel.get_full_name() or mov.responsavel.username
            ])
        return response
    
    return render(request, 'relatorio_movimentacoes.html', {
        'movimentacoes': movimentacoes,
        'locais': locais,
    })

@login_required
def relatorio_pdf(request):
    local = request.GET.get('local', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    movimentacoes = Movimentacao.objects.all().order_by('-data')
    
    if local:
        movimentacoes = movimentacoes.filter(
            models.Q(local_anterior=local) | 
            models.Q(novo_local=local)
        )
        
    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
        
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="movimentacoes_{local or "todos"}.pdf"'
    
    # Configurar página em paisagem
    pdf_pagesize = landscape(letter)
    p = canvas.Canvas(response, pagesize=pdf_pagesize)
    width, height = pdf_pagesize  # Agora width > height
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Cabeçalho
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Relatório de Movimentações")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"Local: {local if local else 'Todos os locais'}")
    p.drawString(50, height - 100, f"Data de emissão: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Dados da tabela
    data = [
        [
            Paragraph('<b>Data</b>', styles['Normal']),
            Paragraph('<b>Tombo</b>', styles['Normal']),
            Paragraph('<b>Descrição</b>', styles['Normal']),
            Paragraph('<b>Local Anterior</b>', styles['Normal']),
            Paragraph('<b>Novo Local</b>', styles['Normal']),
            Paragraph('<b>Responsável</b>', styles['Normal'])
        ]
    ]
    
    for mov in movimentacoes:
        data.append([
            mov.data.strftime("%d/%m/%Y %H:%M"),
            mov.item.tombo,
            Paragraph(mov.item.descricao, styles['Normal']),
            mov.local_anterior[0:30],
            mov.novo_local[0:30],
            mov.responsavel.get_full_name() or mov.responsavel.username
        ])

    # Configurar tabela
    table = Table(data, colWidths=[90, 60, 170, 170, 170, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4F81BD')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#DCE6F1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#B8CCE4')),
        ('WORDWRAP', (2,1), (2,-1), 'CJK'),  # Quebra de linha para descrição
    ]))

    # Posicionar tabela
    table.wrapOn(p, width - 100, height - 150)
    table.drawOn(p, 50, height - 450)  # Ajuste para paisagem

    p.showPage()
    p.save()
    
    return response

@login_required
def buscar_locais(request):
    termo = request.GET.get('term', '')
    locais = Item.objects.filter(
        local_oficial__icontains=termo
    ).values_list('local_oficial', flat=True).distinct()[:10]
    
    return JsonResponse(list(locais), safe=False)