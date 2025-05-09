from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Item, Movimentacao, Responsavel
from django.db import transaction, models
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
import csv
import logging
from django.utils import timezone

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
    # Total de itens e não escaneados
    total_geral = Item.objects.count()
    nao_escaneados = Item.objects.filter(local_atual='').count()
    
    # Agrupar por local oficial
    locais = []
    for local_oficial in Item.objects.values('local_oficial').distinct():
        loc = local_oficial['local_oficial']
        
        # Itens que DEVEM estar neste local
        localizados = Item.objects.filter(local_oficial=loc, local_atual=loc)
        nao_localizados = Item.objects.filter(local_oficial=loc).exclude(local_atual=loc)
        
        # Itens que FORAM transferidos para este local
        transferidos = Item.objects.filter(local_atual=loc).exclude(local_oficial=loc)
        
        locais.append({
            'nome': loc,
            'localizados': localizados,
            'nao_localizados': nao_localizados,
            'transferidos': transferidos,
            'total': localizados.count() + nao_localizados.count()
        })

    context = {
        'total_geral': total_geral,
        'nao_escaneados': nao_escaneados,
        'locais': locais
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
    movimentacoes = Movimentacao.objects.all().order_by('-data')
    
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
    
    return render(request, 'relatorio_movimentacoes.html', {'movimentacoes': movimentacoes})

@login_required
def buscar_locais(request):
    termo = request.GET.get('term', '')
    locais = Item.objects.filter(
        local_oficial__icontains=termo
    ).values_list('local_oficial', flat=True).distinct()[:10]
    
    return JsonResponse(list(locais), safe=False)