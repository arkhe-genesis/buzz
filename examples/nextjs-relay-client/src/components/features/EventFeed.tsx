'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppSelector } from '@/store/store';
import styles from './EventFeed.module.scss';

// Componente para renderizar um evento individual baseado no Kind (NIP)
function EventRow({ event }: { event: any }) {
  const isSystem = event.kind === 1000;
  const isMedia = event.tags?.some((t: string[]) => t[0] === 'media');

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, height: 0 }}
      className={`${styles.row} ${isSystem ? styles.system : ''} ${isMedia ? styles.media : ''}`}
    >
      <div className={styles.meta}>
        <span className={styles.kind}>Kind {event.kind}</span>
        <span className={styles.time}>
          {new Date(event.created_at * 1000).toLocaleTimeString('pt-BR')}
        </span>
      </div>
      <p className={styles.content}>
        {event.content.substring(0, 150)}{event.content.length > 150 ? '...' : ''}
      </p>

      {/* Renderiza preview de imagens se for upload Blossom */}
      {isMedia && (
        <div className={styles.mediaGrid}>
          {event.tags.filter((t: string[]) => t[0] === 'media').map((t: string[], i: number) => (
            <img key={i} src={t[1]} alt="Upload" className={styles.mediaThumb} loading="lazy" />
          ))}
        </div>
      )}
    </motion.div>
  );
}

export default function EventFeed() {
  const events = useAppSelector((state: any) => state.relay.events);
  // Converte o objeto de eventos em array e ordena por tempo decrescente
  const sortedEvents = Object.values(events).sort((a: any, b: any) => b.created_at - a.created_at);

  return (
    <section className={styles.container} aria-label="Feed de eventos em tempo real">
      <AnimatePresence mode="popLayout">
        {sortedEvents.map((evt: any) => (
          <EventRow key={evt.id} event={evt} />
        ))}
      </AnimatePresence>
    </section>
  );
}
