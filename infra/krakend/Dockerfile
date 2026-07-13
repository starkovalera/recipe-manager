FROM krakend:2.13.8 AS validator

COPY krakend.json /etc/krakend/krakend.json
RUN krakend check -tnc /etc/krakend/krakend.json

FROM krakend:2.13.8

COPY --from=validator \
    --chown=krakend:nogroup \
    /etc/krakend/krakend.json \
    /etc/krakend/krakend.json

CMD ["run", "-c", "/etc/krakend/krakend.json"]
