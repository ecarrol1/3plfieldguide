FROM python:3.12-alpine AS build
WORKDIR /app
COPY build.py data.json ./
ARG SITE_URL=""
RUN python build.py --test && if [ -n "$SITE_URL" ]; then python build.py --site-url "$SITE_URL"; else python build.py; fi
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
