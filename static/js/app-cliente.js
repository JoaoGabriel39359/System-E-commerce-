const { createApp } = Vue;

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

            // Configurações lidas do HTML após o mount (evita DOM access em computed)
            nutellaGratisAtiva: false,
            whatsappVendedor: '',
            lojaAbertaAtiva: true,

            // Controle do modal de confirmação pós-adição
            modalAdicionadoAberto: false,
            ultimoItemAdicionado: null,

            // Controle do toast de aviso (ex: limite de recheios)
            toastMensagem: '',
            toastTimer: null,

            // Dica 4: Estado da conexão de internet
            isOffline: !navigator.onLine,

            ingredientesDisponiveis: [],
            ingredientesMap: {},
            bairrosMap: {}
        }
    },
    mounted() {
        // Monitora desconexão com a internet (Dica 4)
        window.addEventListener('online', () => {
            this.isOffline = false;
            this.mostrarToast('Sua conexão de internet retornou! 🟢');
        });
        window.addEventListener('offline', () => {
            this.isOffline = true;
        });

        // Lê as configurações dos inputs hidden com segurança após o DOM estar pronto
        this.nutellaGratisAtiva = document.getElementById('nutella_gratis_config')?.value === 'true';
        this.whatsappVendedor = document.getElementById('whatsapp_vendedor_config')?.value || '';
        this.lojaAbertaAtiva = document.getElementById('loja_aberta_config')?.value !== 'false';

        // Carrega os dados JSON iniciais renderizados pelo backend se existirem
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

        // Dica 5: Conexão SSE (Server-Sent Events) para atualizações push instantâneas em tempo real
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
                eventSource.onerror = () => {
                    // Se falhar a transmissão contínua (ex: oscilação de rede), o polling serve de backup
                };
            } catch (errSse) {
                console.warn("EventSource indisponível, usando polling de backup:", errSse);
            }
        }

        // Polling tradicional de backup a cada 10 segundos
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
            if (this.recheiosSelecionados.includes("Nutella") && !this.nutellaGratisAtiva) {
                if (this.tamanhoSelecionado === 22) return 2.00;
                if (this.tamanhoSelecionado === 27) return 3.00;
                if (this.tamanhoSelecionado === 37) return 5.00;
                return 3.00;
            }
            return 0.00;
        },
        // Calcula o valor do copo que está sendo montado na tela agora
        precoItemAtual() {
            if (!this.tamanhoSelecionado) return 0.00;
            return this.tamanhoSelecionado + this.adicionalNutella;
        },
        // Calcula a soma de TODOS os copos que já estão no carrinho
        subtotalItens() {
            return this.itensNoCarrinho.reduce((soma, item) => soma + item.precoTotal, 0);
        },
        totalCarrinhoComEntrega() {
            return this.subtotalItens + this.taxaEntrega;
        },
        // Soma os itens + a taxa de entrega única
        totalPedido() {
            return this.subtotalItens + this.precoItemAtual + this.taxaEntrega;
        },
        totalFormatado() {
            return this.totalPedido.toFixed(2).replace('.', ',');
        }
    },
    methods: {
        processarAtualizacaoStatus(data) {
            if (!data) return;

            // 1. Loja aberta
            if (data.loja_aberta !== undefined) {
                this.lojaAbertaAtiva = data.loja_aberta;
            }

            // 2. Nutella grátis
            if (data.nutella_gratis !== undefined) {
                this.nutellaGratisAtiva = data.nutella_gratis;
            }

            // 3. Ingredientes
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

            // 4. Bairros e taxas de entrega
            if (data.bairros) {
                this.bairrosMap = data.bairros;

                if (this.bairroSelecionado && this.bairrosMap[this.bairroSelecionado] !== undefined) {
                    const novaTaxa = parseFloat(this.bairrosMap[this.bairroSelecionado]);
                    if (this.taxaEntrega !== novaTaxa) {
                        this.taxaEntrega = novaTaxa;
                        this.mostrarToast(`Taxa de entrega de ${this.bairroSelecionado} atualizada: R$ ${novaTaxa.toFixed(2).replace('.', ',')} 🛵`);
                    }
                }
            }
        },

        // Exibe um toast de aviso no topo da tela por alguns segundos
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
            this.taxaEntrega = parseFloat(taxa);
            this.abrirDropdownBairro = false;
        },

        // Pega o copo atual e joga no carrinho, abrindo o modal de confirmação
        adicionarAoCarrinho() {
            if (!this.tamanhoSelecionado) {
                this.mostrarToast('Por favor, escolha o tamanho do seu pote primeiro! 🍿');
                return;
            }

            if (this.recheiosSelecionados.length === 0) {
                this.mostrarToast('Selecione pelo menos 1 recheio para montar seu pote! 😊');
                return;
            }

            // Cria uma cópia do copo atual montado
            const novoItem = {
                id: Date.now(),
                tamanhoLabel: this.labelTamanho,
                recheios: [...this.recheiosSelecionados],
                adicionalNutella: this.adicionalNutella,
                precoTotal: this.precoItemAtual
            };

            this.itensNoCarrinho.push(novoItem);

            // Guarda referência do item para exibir no modal
            this.ultimoItemAdicionado = novoItem;
            this.modalAdicionadoAberto = true;

            // Reseta a montagem para o cliente poder escolher outro
            this.recheiosSelecionados = [];
            this.tamanhoSelecionado = null;
        },

        // Fecha o modal de confirmação e deixa o cliente montar mais
        continuarAdicionando() {
            this.modalAdicionadoAberto = false;
            this.ultimoItemAdicionado = null;
            // Rola suavemente de volta ao topo para montar outro copo
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },

        // Fecha o modal de confirmação e abre o carrinho
        irParaCarrinhoDoModal() {
            this.modalAdicionadoAberto = false;
            this.ultimoItemAdicionado = null;
            this.carrinhoAberto = true;
        },

        // Permite o cliente tirar um item do carrinho
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
        irParaO_Checkout() {
            this.carrinhoAberto = false;
            setTimeout(() => {
                const checkoutSection = document.getElementById('checkout');
                if (checkoutSection) {
                    checkoutSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 180);
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
            if (!this.bairroSelecionado) {
                this.mostrarToast('Por favor, selecione seu bairro de entrega.');
                return;
            }
            if (!this.enderecoRua.trim()) {
                this.mostrarToast('Por favor, informe o nome da sua rua.');
                return;
            }
            if (!this.enderecoNumero.trim()) {
                this.mostrarToast('Por favor, informe o número da sua residência (ou coloque S/N).');
                return;
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

            let enderecoFinalParaO_Python = `${this.enderecoRua.trim()}, Nº ${this.enderecoNumero.trim()}`;
            if (this.enderecoComplemento.trim()) {
                enderecoFinalParaO_Python += ` - ${this.enderecoComplemento.trim()}`;
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

            const textoWhatsApp =
                `🍫 *NOVO PEDIDO - DOCERIA DIVINO RECHEIO* 🍫\n\n` +
                `👤 *CLIENTE:*\n` +
                `• *Nome:* ${this.nomeCliente.trim()}\n` +
                `• *Telefone:* ${this.telefoneCliente.trim()}\n` +
                `• *Endereço:* ${enderecoFinalParaO_Python}\n` +
                `• *Bairro:* ${this.bairroSelecionado}\n\n` +
                `🛒 *PRODUTOS PEDIDOS:*\n${itensTextoWhatsApp}` +
                `💰 *PAGAMENTO & ENTREGA:*\n` +
                `• *Forma de Pagamento:* ${textoFormaPagamento}\n` +
                `• *Taxa de Entrega:* R$ ${this.taxaEntrega.toFixed(2).replace('.', ',')}\n` +
                `• *Total Geral:* R$ ${this.totalFormatado}\n\n` +
                `_Pedido enviado do cardápio digital._`;

            this.linkWhatsPendente = this.whatsappVendedor
                ? `https://api.whatsapp.com/send?phone=${this.whatsappVendedor}&text=${encodeURIComponent(textoWhatsApp)}`
                : `https://api.whatsapp.com/send?text=${encodeURIComponent(textoWhatsApp)}`;

            this.pedidoSucesso = true;

            // Formatação para o backend do admin
            const nomesTamanhosUnificados = this.itensNoCarrinho.map(i => i.tamanhoLabel).join(' + ');
            const recheiosUnificadosArray = this.itensNoCarrinho.map(i => `${i.tamanhoLabel}(${i.recheios.join(', ')})`);
            const totalNutellaGeral = this.itensNoCarrinho.reduce((s, i) => s + i.adicionalNutella, 0);

            const payload = {
                nome: this.nomeCliente.trim(),
                telefone: this.telefoneCliente.trim(),
                endereco: enderecoFinalParaO_Python,
                bairro: this.bairroSelecionado,
                tamanho: nomesTamanhosUnificados,
                recheios: recheiosUnificadosArray,
                adicional_nutella: totalNutellaGeral,
                forma_pagamento: textoFormaPagamento,
                taxa_entrega: this.taxaEntrega,
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