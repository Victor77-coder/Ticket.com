"use client";

import jsQR from "jsqr";
import { useCallback, useEffect, useRef, useState } from "react";

import estilos from "./gate.module.css";

/**
 * A leitura do QR pela câmera.
 *
 * Os quadros do vídeo vão para um `<canvas>` e o decodificador roda sobre os
 * pixels. `jsQR` é JavaScript puro, sem dependências transitivas — decodificar
 * QR é um padrão publicado com casos de borda reais (localização de padrões,
 * correção de erro, perspectiva, binarização sob luz irregular), e é o outro
 * lado do mesmo argumento que trouxe `qrcode` ao servidor na 008.
 *
 * UMA APRESENTAÇÃO, UM DESFECHO — e esta é a parte que só se descobre com a
 * câmera na mão. Um QR parado na frente da lente decodifica dezenas de vezes
 * por segundo. Sem tratamento, a primeira leitura marca o uso e a segunda — 40
 * ms depois, do mesmo aparelho, da mesma pessoa — responde "já utilizado". O
 * sistema estaria INTEIRAMENTE CORRETO e a portaria veria uma contradição.
 *
 * Idempotência no servidor NÃO resolve isso: ela garante que o estado não se
 * corrompe, não que a pessoa não veja duas respostas contraditórias. É defeito
 * de interface causado por característica do hardware, e só se conserta aqui.
 *
 * As três regras somadas:
 *   1. enquanto uma validação está em andamento, o laço não dispara outra;
 *   2. o MESMO conteúdo decodificado é ignorado por alguns segundos;
 *   3. o desfecho não se apaga sozinho (isso é da tela, não deste componente).
 *
 * E A CÂMERA EXIGE CONTEXTO SEGURO: `localhost` conta, IP de rede local não, e
 * nenhuma configuração da aplicação muda isso. Quem abrir a portaria pelo
 * celular via IP não terá câmera — por isso a digitação manual está SEMPRE
 * visível, e não escondida atrás desta falha.
 */

const IGNORAR_REPETICAO_MS = 4000;

type Props = {
  /** Chamado com o conteúdo decodificado. */
  aoLer: (codigo: string) => void;
  /** Enquanto `true`, o laço não dispara nova leitura (regra 1). */
  ocupado: boolean;
};

type EstadoDaCamera = "iniciando" | "lendo" | "indisponivel";

export default function LeitorDeCodigo({ aoLer, ocupado }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ultimoRef = useRef<{ codigo: string; quando: number } | null>(null);
  const ocupadoRef = useRef(ocupado);
  const [estado, setEstado] = useState<EstadoDaCamera>("iniciando");

  // O laço lê a referência, não o prop: recriar o laço a cada mudança de
  // `ocupado` reiniciaria a câmera a cada validação.
  useEffect(() => {
    ocupadoRef.current = ocupado;
  }, [ocupado]);

  const decodificar = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState !== video.HAVE_ENOUGH_DATA) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const contexto = canvas.getContext("2d", { willReadFrequently: true });
    if (!contexto) return;

    contexto.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imagem = contexto.getImageData(0, 0, canvas.width, canvas.height);
    const achado = jsQR(imagem.data, imagem.width, imagem.height);
    if (!achado?.data) return;

    // Regra 1: uma validação por vez.
    if (ocupadoRef.current) return;

    // Regra 2: a mesma apresentação não vira duas validações.
    const agora = Date.now();
    const ultimo = ultimoRef.current;
    if (
      ultimo &&
      ultimo.codigo === achado.data &&
      agora - ultimo.quando < IGNORAR_REPETICAO_MS
    ) {
      return;
    }

    ultimoRef.current = { codigo: achado.data, quando: agora };
    aoLer(achado.data);
  }, [aoLer]);

  useEffect(() => {
    let fluxo: MediaStream | null = null;
    let timer: number | null = null;
    let vivo = true;

    async function abrir() {
      if (!navigator.mediaDevices?.getUserMedia) {
        // Sem câmera no aparelho, ou fora de contexto seguro. É estado
        // normal, nunca erro — e a digitação continua ao lado.
        setEstado("indisponivel");
        return;
      }
      try {
        fluxo = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        if (!vivo) {
          fluxo.getTracks().forEach((t) => t.stop());
          return;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = fluxo;
          await videoRef.current.play();
        }
        setEstado("lendo");
        timer = window.setInterval(decodificar, 120);
      } catch {
        // Permissão negada, ou revogada depois de concedida.
        setEstado("indisponivel");
      }
    }

    abrir();

    return () => {
      vivo = false;
      if (timer) window.clearInterval(timer);
      fluxo?.getTracks().forEach((t) => t.stop());
    };
  }, [decodificar]);

  if (estado === "indisponivel") {
    return (
      <div className={estilos.cameraIndisponivel} role="status">
        <p className={estilos.cameraTitulo}>Leitura por câmera indisponível</p>
        <p className={estilos.cameraTexto}>
          O navegador não liberou a câmera neste aparelho. Peça o código escrito no
          ingresso e digite no campo ao lado — o resultado é o mesmo.
        </p>
      </div>
    );
  }

  return (
    <div className={estilos.camera}>
      <video ref={videoRef} className={estilos.video} muted playsInline />
      <canvas ref={canvasRef} className={estilos.canvasOculto} />
      <p className={estilos.cameraDica} role="status">
        {estado === "iniciando"
          ? "Abrindo a câmera…"
          : "Aponte para o código do ingresso."}
      </p>
    </div>
  );
}
