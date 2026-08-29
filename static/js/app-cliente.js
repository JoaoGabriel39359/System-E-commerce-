const { createApp } = Vue;

function getJsonInicial(id) {
    try {
        const elem = document.getElementById(id);
        if (elem && elem.textContent) {
            return JSON.parse(elem.textContent);
        }
    } catch (e) {
        console.error("Erro ao carregar dados iniciais:", id, e);
    }
    return {};
}

createApp({
    data() {
        return {
            // Controle de telas
            carrinhoAberto: false,
            pedidoSucesso: false,

            // Controle do Menu Flutuante Customizado de Bairros (Estilo iFood)
            abrirDropdownBairro: false,
            buscaBairro: '',
            bairroSelecionado: '',
            taxaEntrega: 0.00,

            linkWhatsPendente: '',

            // Rascunho do produto ATUAL sendo montado
            tamanhoSelecionado: null,
            recheiosSelecionados: [],
            nutellaSelecionada: false,

            // NOVO: Controle de Tipo de Entrega ('entrega' ou 'retirada')
            tipoEntrega: 'entrega',

            // Array que guarda todos os copos adicionados ao carrinho
            itensNoCarrinho: [],

            // Dados do Cliente
            nomeCliente: '',
            telefoneCliente: '',
            enderecoRua: '',
            enderecoNumero: '',
            enderecoComplemento: '',
            formaPagamento: '',
            precisaTroco: null,
            valorTroco: '',

            // Configurações lidas do HTML após o mount
            nutellaGratisAtiva: false,
            whatsappVendedor: '',
            lojaAbertaAtiva: true,

            // Controle do modal de confirmação pós-adição
            modalAdicionadoAberto: false,
            ultimoItemAdicionado: null,

            // Controle do toast de aviso
            toastMensagem: '',
            toastTimer: null,

            // Estado da conexão de internet
            isOffline: !navigator.onLine,

            ingredientesDisponiveis: [],
            ingredientesMap: getJsonInicial('initial-ingredientes'),
            bairrosMap: getJsonInicial('initial-bairros')
        }
    },
    mounted() {
        // 1. Monitora desconexão com a internet
        window.addEventListener('online', () => {
            this.isOffline = false;
            this.mostrarToast('Sua conexão de internet retornou! 🟢');
        });
        window.addEventListener('offline', () => {
            this.isOffline = true;
        });

        // 2. Lê as configurações dos inputs hidden vindos do HTML/Python
        const inputNutella = document.getElementById('nutella_gratis_config');
        if (inputNutella) {
            this.nutellaGratisAtiva = inputNutella.value === 'true';
        }

        this.whatsappVendedor = document.getElementById('whatsapp_vendedor_config')?.value || '';
        this.lojaAbertaAtiva = document.getElementById('loja_aberta_config')?.value !== 'false';

        // 3. Carrega os dados JSON iniciais renderizados pelo backend se existirem
        try {
            const ingElem = document.getElementById('initial-ingredientes');
            if (ingElem && ingElem.textContent) {
                this.ingredientesMap = JSON.parse(ingElem.textContent);
            }
            const bairrosElem = document.getElementById('initial-bairros');
            if (bairrosElem && bairrosElem.textContent) {
                this.bairrosMap = JSON.parse(bairrosElem.textContent);
            }
        } catch (e) {
            console.error("Erro ao carregar dados iniciais no JS:", e);
        }

        // 4. Conexão SSE (Server-Sent Events) para atualizações em tempo real
        if (window.EventSource) {
            try {
                const eventSource = new EventSource('/admin/api/status-stream');
                eventSource.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.processarAtualizacaoStatus(data);
                        this.isOffline = false;
                    } catch (e) {
                        console.error("Erro ao processar pacote SSE:", e);
                    }
                };
                eventSource.onerror = () => { };
            } catch (errSse) {
                console.warn("EventSource indisponível, usando polling de backup:", errSse);
            }
        }

        // 5. Polling de backup a cada 10 segundos
        setInterval(async () => {
            try {
                const response = await fetch('/admin/api/status-loja');
                if (response.ok) {
                    const data = await response.json();
                    this.processarAtualizacaoStatus(data);
                    this.isOffline = false;
                }
            } catch (err) {
                if (!navigator.onLine) {
                    this.isOffline = true;
                }
                console.error("Erro no polling de status:", err);
            }
        }, 10000);
    },
    computed: {
        labelTamanho() {
            if (this.tamanhoSelecionado === 22) return "350ML";
            if (this.tamanhoSelecionado === 27) return "500ML";
            if (this.tamanhoSelecionado === 37) return "1L";
            return "";
        },
        adicionalNutella() {
            if (!this.nutellaSelecionada || this.nutellaGratisAtiva) {
                return 0.00;
            }
            if (this.tamanhoSelecionado === 22) return 2.00;
            if (this.tamanhoSelecionado === 27) return 3.00;
            if (this.tamanhoSelecionado === 37) return 5.00;
            return 3.00;
        },
        precoItemAtual() {
            if (!this.tamanhoSelecionado) return 0.00;
            return this.tamanhoSelecionado + this.adicionalNutella;
        },
        subtotalItens() {
            return this.itensNoCarrinho.reduce((soma, item) => soma + item.precoTotal, 0);
        },
        totalCarrinhoComEntrega() {
            return this.subtotalItens + (this.tipoEntrega === 'retirada' ? 0 : this.taxaEntrega);
        },
        totalPedido() {
            return this.subtotalItens + this.precoItemAtual + (this.tipoEntrega === 'retirada' ? 0 : this.taxaEntrega);
        },
        totalFormatado() {
            return this.totalPedido.toFixed(2).replace('.', ',');
        }
    },

    watch: {
        nutellaGratisAtiva(novoValor) {
            if (novoValor) {
                this.mostrarToast('🎉 Oba! Nutella está GRÁTIS hoje!');
            }
        }
    },

    methods: {
        // NOVO: Alterna entre entrega e retirada na loja zerando/recalculando a taxa
        selecionarTipoEntrega(tipo) {
            this.tipoEntrega = tipo;
            if (tipo === 'retirada') {
                this.taxaEntrega = 0.00;
            } else if (this.bairroSelecionado && this.bairrosMap[this.bairroSelecionado] !== undefined) {
                this.taxaEntrega = parseFloat(this.bairrosMap[this.bairroSelecionado]);
            }
        },

        processarAtualizacaoStatus(data) {
            if (!data) return;

            if (data.loja_aberta !== undefined) {
                this.lojaAbertaAtiva = data.loja_aberta;
            }

            if (data.nutella_gratis !== undefined) {
                this.nutellaGratisAtiva = (data.nutella_gratis === true || data.nutella_gratis === 'true');
            }

            if (data.ingredientes) {
                this.ingredientesMap = data.ingredientes;
                this.recheiosSelecionados = this.recheiosSelecionados.filter(nome => {
                    if (this.ingredientesMap[nome] && !this.ingredientesMap[nome].disponivel) {
                        this.mostrarToast(`O recheio "${nome}" ficou indisponível no momento! 🍿`);
                        return false;
                    }
                    return true;
                });
            }

            if (data.bairros) {
                this.bairrosMap = data.bairros;
                if (this.tipoEntrega === 'entrega' && this.bairroSelecionado && this.bairrosMap[this.bairroSelecionado] !== undefined) {
                    const novaTaxa = parseFloat(this.bairrosMap[this.bairroSelecionado]);
                    if (this.taxaEntrega !== novaTaxa) {
                        this.taxaEntrega = novaTaxa;
                        this.mostrarToast(`Taxa de entrega de ${this.bairroSelecionado} atualizada: R$ ${novaTaxa.toFixed(2).replace('.', ',')} 🛵`);
                    }
                }
            }
        },

        mostrarToast(mensagem, duracao = 3000) {
            if (this.toastTimer) clearTimeout(this.toastTimer);
            this.toastMensagem = mensagem;
            this.toastTimer = setTimeout(() => {
                this.toastMensagem = '';
            }, duracao);
        },

        validarLimite() {
            if (this.recheiosSelecionados.length > 3) {
                this.recheiosSelecionados.pop();
                this.mostrarToast('Máximo de 3 recheios por pote! 🍿');
            }
        },
        toggleDropdownBairro() {
            this.abrirDropdownBairro = !this.abrirDropdownBairro;
            if (this.abrirDropdownBairro) {
                this.buscaBairro = '';
                this.$nextTick(() => {
                    this.$refs.inputBuscaBairro?.focus();
                });
            }
        },
        filtrarBairro(nomeBairro) {
            if (!this.buscaBairro) return true;
            return nomeBairro.toLowerCase().includes(this.buscaBairro.toLowerCase());
        },
        clicarNoBairro(bairro, taxa) {
            this.bairroSelecionado = bairro;
            if (this.tipoEntrega === 'entrega') {
                this.taxaEntrega = parseFloat(taxa);
            }
            this.abrirDropdownBairro = false;
        },

        adicionarAoCarrinho() {
            if (!this.tamanhoSelecionado) {
                this.mostrarToast('Por favor, escolha o tamanho do seu pote primeiro! 🍿');
                return;
            }

            if (this.recheiosSelecionados.length === 0) {
                this.mostrarToast('Selecione pelo menos 1 recheio para montar seu pote! 😊');
                return;
            }

            let recheiosFinais = [...this.recheiosSelecionados];
            if (this.nutellaSelecionada) {
                const labelNutella = this.nutellaGratisAtiva ? 'Nutella (Grátis 🎉)' : 'Nutella (Adicional 🍫)';
                recheiosFinais.push(labelNutella);
            }

            const novoItem = {
                id: Date.now(),
                tamanhoLabel: this.labelTamanho,
                recheios: recheiosFinais,
                temNutellaIsolada: this.nutellaSelecionada,
                adicionalNutella: this.adicionalNutella,
                precoTotal: this.precoItemAtual
            };

            this.itensNoCarrinho.push(novoItem);
            this.ultimoItemAdicionado = novoItem;
            this.modalAdicionadoAberto = true;

            this.recheiosSelecionados = [];
            this.tamanhoSelecionado = null;
            this.nutellaSelecionada = false;
        },

        continuarAdicionando() {
            this.modalAdicionadoAberto = false;
            this.ultimoItemAdicionado = null;
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },

        irParaCarrinhoDoModal() {
            this.modalAdicionadoAberto = false;
            this.ultimoItemAdicionado = null;
            this.carrinhoAberto = true;
        },

        removerItemCarrinho(id) {
            this.itensNoCarrinho = this.itensNoCarrinho.filter(item => item.id !== id);
        },

        irParaO_Carrinho() {
            if (this.itensNoCarrinho.length === 0) {
                this.mostrarToast('Seu carrinho está vazio! Monte um pote primeiro. 🛒');
                return;
            }
            this.carrinhoAberto = true;
        },
        voltarParaO_Cardapio() {
            this.carrinhoAberto = false;
        },
        irParaLinkWhatsApp() {
            if (this.linkWhatsPendente) {
                window.location.href = this.linkWhatsPendente;
            }
        },

        async enviarPedido() {
            if (!this.lojaAbertaAtiva) {
                this.mostrarToast('Desculpe, a loja fechou e não está mais aceitando pedidos hoje. 🛑');
                return;
            }
            if (this.itensNoCarrinho.length === 0) {
                this.mostrarToast('Adicione pelo menos um produto ao carrinho antes de finalizar.');
                return;
            }
            if (!this.nomeCliente.trim()) {
                this.mostrarToast('Por favor, digite seu nome completo.');
                return;
            }
            if (!this.telefoneCliente.trim()) {
                this.mostrarToast('Por favor, informe seu telefone/WhatsApp.');
                return;
            }

            // VALIDAÇÕES CONDICIONAIS DE ACORDO COM O TIPO DE ENTREGA
            if (this.tipoEntrega === 'entrega') {
                if (!this.bairroSelecionado) {
                    this.mostrarToast('Por favor, selecione seu bairro para entrega.');
                    return;
                }
                if (!this.enderecoRua.trim()) {
                    this.mostrarToast('Por favor, informe o nome da sua rua.');
                    return;
                }
                if (!this.enderecoNumero.trim()) {
                    this.mostrarToast('Por favor, informe o número da sua residência (ou S/N).');
                    return;
                }
            }

            if (!this.formaPagamento) {
                this.mostrarToast('Por favor, selecione uma forma de pagamento.');
                return;
            }

            let textoFormaPagamento = '';
            if (this.formaPagamento === 'dinheiro') {
                if (this.precisaTroco === null) {
                    this.mostrarToast('Por favor, informe se precisa de troco.');
                    return;
                }
                if (this.precisaTroco === 'sim' && !this.valorTroco.trim()) {
                    this.mostrarToast('Por favor, informe o valor para o troco.');
                    return;
                }
                textoFormaPagamento = this.precisaTroco === 'sim'
                    ? `Dinheiro 💵 (Troco para R$ ${this.valorTroco})`
                    : 'Dinheiro 💵 (Não precisa de troco)';
            } else {
                const pagamentosMap = {
                    'pix': 'Pix ⚡',
                    'credito': 'Cartão de Crédito 💳',
                    'debito': 'Cartão de Débito 💳'
                };
                textoFormaPagamento = pagamentosMap[this.formaPagamento];
            }

            // PREPARA OS CAMPOS DE ACORDO COM ENTREGA OU RETIRADA
            let enderecoFinalParaO_Python = '';
            let bairroFinal = '';

            if (this.tipoEntrega === 'retirada') {
                bairroFinal = 'Retirada na Loja';
                enderecoFinalParaO_Python = 'RETIRADA NO BALCAO';
            } else {
                bairroFinal = this.bairroSelecionado;
                enderecoFinalParaO_Python = `${this.enderecoRua.trim()}, Nº ${this.enderecoNumero.trim()}`;
                if (this.enderecoComplemento.trim()) {
                    enderecoFinalParaO_Python += ` - ${this.enderecoComplemento.trim()}`;
                }
            }

            // Formatação do texto de múltiplos itens para o WhatsApp
            let itensTextoWhatsApp = "";
            this.itensNoCarrinho.forEach((item, index) => {
                itensTextoWhatsApp += `🍿 *Pote #${index + 1} (${item.tamanhoLabel})*\n`;
                itensTextoWhatsApp += `• Recheios: ${item.recheios.join(', ')}\n`;
                if (item.adicionalNutella > 0) {
                    itensTextoWhatsApp += `• Adicional Nutella: R$ ${item.adicionalNutella.toFixed(2).replace('.', ',')}\n`;
                }
                itensTextoWhatsApp += `• Valor do Pote: R$ ${item.precoTotal.toFixed(2).replace('.', ',')}\n\n`;
            });

            const tipoEntregaTextoWhats = this.tipoEntrega === 'retirada'
                ? `🏪 *RETIRADA NA LOJA*`
                : `🛵 *DELIVERY / ENTREGA*`;

            const textoWhatsApp =
                `🍫 *NOVO PEDIDO - DOCERIA DIVINO RECHEIO* 🍫\n\n` +
                `📌 *MODO:* ${tipoEntregaTextoWhats}\n` +
                `👤 *CLIENTE:*\n` +
                `• *Nome:* ${this.nomeCliente.trim()}\n` +
                `• *Telefone:* ${this.telefoneCliente.trim()}\n` +
                (this.tipoEntrega === 'entrega'
                    ? `• *Endereço:* ${enderecoFinalParaO_Python}\n• *Bairro:* ${bairroFinal}\n\n`
                    : `\n`) +
                `🛒 *PRODUTOS PEDIDOS:*\n${itensTextoWhatsApp}` +
                `💰 *PAGAMENTO:* ${textoFormaPagamento}\n` +
                `🛵 *Taxa de Entrega:* R$ ${(this.tipoEntrega === 'retirada' ? 0 : this.taxaEntrega).toFixed(2).replace('.', ',')}\n` +
                `💵 *Total Geral:* R$ ${this.totalFormatado}\n\n` +
                `_Pedido enviado do cardápio digital._`;

            this.linkWhatsPendente = this.whatsappVendedor
                ? `https://api.whatsapp.com/send?phone=${this.whatsappVendedor}&text=${encodeURIComponent(textoWhatsApp)}`
                : `https://api.whatsapp.com/send?text=${encodeURIComponent(textoWhatsApp)}`;

            this.pedidoSucesso = true;

            // Formatação para o backend
            const nomesTamanhosUnificados = this.itensNoCarrinho.map(i => i.tamanhoLabel).join(' + ');
            const recheiosUnificadosArray = this.itensNoCarrinho.map(i => `${i.tamanhoLabel}(${i.recheios.join(', ')})`);
            const totalNutellaGeral = this.itensNoCarrinho.reduce((s, i) => s + i.adicionalNutella, 0);

            const payload = {
                nome: this.nomeCliente.trim(),
                telefone: this.telefoneCliente.trim(),
                endereco: enderecoFinalParaO_Python,
                bairro: bairroFinal,
                tamanho: nomesTamanhosUnificados,
                recheios: recheiosUnificadosArray,
                adicional_nutella: totalNutellaGeral,
                forma_pagamento: textoFormaPagamento,
                taxa_entrega: this.tipoEntrega === 'retirada' ? 0.00 : this.taxaEntrega,
                total: this.totalPedido
            };

            try {
                await fetch('/admin/pedidos/novo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } catch (err) {
                console.error("Erro interno ao tentar registrar pedido no painel administrador:", err);
            }
        }
    }
}).mount('#app');