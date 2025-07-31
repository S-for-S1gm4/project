FROM nginx:alpine

# Удаляем дефолтную конфигурацию
RUN rm /etc/nginx/conf.d/default.conf

# Копируем нашу конфигурацию
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем директории для логов
RUN mkdir -p /var/log/nginx

# Экспонируем порты
EXPOSE 80 443

# Запускаем nginx
CMD ["nginx", "-g", "daemon off;"]