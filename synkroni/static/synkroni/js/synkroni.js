(function () {
  /*
   * Luo Websocket-palvelinyhteys.
   */
  const {
    websocket,
    protokolla,
    kattely,
  } = document.currentScript.dataset;

  function Synkroni() {
    this.osoite = websocket;
    this.protokolla = JSON.parse(protokolla ?? "null");
    this.toimintojono = {}; // toiminto_id: {vastaus, virhe}
    this.yhteys = null;
    this.toiminto_id = 0; // Seuraava käyttämätön toiminto-id.
    this.lahetysjono = [];
    this.kattely = JSON.parse(
      kattely? kattely.replace(/'/g, '"') : "{}"
    );
    this.yhdistaUudelleenAutomaattisesti = false;

    // Alusta `document.toiminto` siten, että
    // `document.toiminto.X(...)` kutsuu metodia
    // `this.toiminto({X: ...})`.
    document.toiminto = new Proxy(this.toiminto.bind(this), {
      get (target, prop) {
        return new Proxy(target, {
          apply (target, _this, args) {
            return target.apply(_this, [{[prop]: args[0]}]);
          }
        });
      },
      apply (target, _this, args) {
        return target.apply(_this, args);
      }
    });

    // Alusta `document.data`.
    let data = JSON.parse(
      document.getElementById("synkroni-alkutilanne").textContent
    );
    if (window.JSONPatcherProxy) {
      this.tarkkailija = new JSONPatcherProxy(data);
      data = this.tarkkailija.observe(
        true, this._lahtevaMuutos.bind(this)
      );
    }
    document.data = data;

    this.__vietavaData = JSON.parse(
      document.getElementById("synkroni-alkutilanne").textContent
    );

    this._avaaYhteys();
  }

  Object.assign(Synkroni.prototype, {
    MAKSIMIDATA: 1024 * 1024,

    _avaaYhteys: function () {
      this.yhteys = new WebSocket(this.osoite, this.protokolla || undefined);
      Object.assign(this.yhteys, {
        onopen: this._yhteysAvattu.bind(this),
        onmessage: this._viestiVastaanotettu.bind(this),
        onclose: this._yhteysKatkaistu.bind(this),
      });
    },
    _yhteysAvattu: function (e) {
      this.yhteys.send(JSON.stringify(this.kattely));
      for (lahteva_sanoma of this.lahetysjono) {
        this._lahetaData(lahteva_sanoma);
      }
      this.lahetysjono = [];
      document.dispatchEvent(
        new Event("yhteys-avattu")
      );

      // Jätä jonoon yhteyskokeilu palvelimelle.
      // Paluusanoman yhteydessä merkitään yhteys avatuksi.
      // Ensimmäisen alustuksen jälkeen avain `uusi` poistetaan
      // kättelydatasta.
      this.toiminto({
        yhteys_alustettu: {},
      }).then(function (data) {
        const uusi = this.kattely.uusi;
        if (uusi) {
          delete this.kattely.uusi;
        }
        this.yhdistaUudelleenAutomaattisesti = true;
        document.dispatchEvent(
          new CustomEvent("yhteys-alustettu", {detail: {uusi: uusi}})
        );
      }.bind(this));
    },
    _yhteysKatkaistu: function (e) {
      document.dispatchEvent(
        new CustomEvent("yhteys-katkaistu", {detail: e})
      );

      // Poista aiempi yhteys.
      this.yhteys = null;

      // Yritä yhteyden muodostamista uudelleen automaattisesti,
      // mikäli yhteys katkesi muusta kuin käyttäjästä
      // johtuvasta syystä.
      if (this.yhdistaUudelleenAutomaattisesti && e.code > 1001)
        window.setTimeout(this._avaaYhteys.bind(this), 200);
    },
    _viestiVastaanotettu: function (e) {
      let data = JSON.parse(e.data);
      if (data.hasOwnProperty("status")) {
        this.yhteys.close();
        if (confirm("Palvelinyhteyden muodostus epäonnistui. Yritetäänkö uudelleen?")) {
          location.reload();
        }
      }
      else if (data.hasOwnProperty("toiminto_id")) {
        const {vastaus, virhe} = this.toimintojono[data.toiminto_id];
        if (data.hasOwnProperty("virhe"))
          virhe(data);
        else
          vastaus(data);
        delete this.toimintojono[data.toiminto_id];
      }
      else if (data.hasOwnProperty("virhe")) {
        alert(data.virhe || "Tuntematon palvelinvirhe");
      }
      else {
        this._saapuvaMuutos(data);
      }
    },

    _lahetaData: function(data) {
      let json = JSON.stringify(data);
      if (json.length <= this.MAKSIMIDATA) {
        this.yhteys.send(json);
      }
      else {
        // Kääri JSON-data määrämittaisiin paketteihin
        // ja lähetä ne erikseen.
        let osat = this._patkiOsiin(
          json.replace(
            /[\\]/g, '\\\\'
          ).replace(
            /[\"]/g, '\\\"'
          ),
          // 21 -> kääreen kehys.
          this.MAKSIMIDATA - 21
        );
        osat.forEach(function (osa, i) {
          this.yhteys.send(
            `{"n": ${osat.length - i - 1}, "o": "${osa}"}`
          );
        }.bind(this))
      }
    },

    _lahtevaMuutos: function (p) {
      jsonpatch.apply(this.__vietavaData, JSON.parse(JSON.stringify(p)));
      if (this.yhteys?.readyState === 1) {
        this._lahetaData(p);
      }
      else {
        // Jätä sanoma jonoon, mikäli yhteyttä ei ole.
        this.lahetysjono.push(p);
      }
    },
    _saapuvaMuutos: function (p) {
      this.tarkkailija?.pause?.();
      jsonpatch.apply(document.data, p);
      jsonpatch.apply(this.__vietavaData, JSON.parse(JSON.stringify(p)));
      this._tulkitseVierasavaimet(document.data);
      this.tarkkailija?.resume?.();
      document.dispatchEvent(
        new Event("data-paivitetty")
      );
    },

    _tulkitseVierasavaimet: function (data) {
      for (let [avain, arvo] of Object.entries(data)) {
        if (Array.isArray(arvo))
          for (let rivi of arvo)
            this._tulkitseVierasavaimet(rivi);
        else if (typeof arvo !== 'object' || arvo === null)
          ;
        else if (arvo.hasOwnProperty("__vierasavain__")) {
          let [
            vierasavain, vierasavain_id
          ] = arvo.__vierasavain__;
          Object.defineProperty(
            data,
            avain,
            {
              get: function () {
                // Poimitaan vierasavain ensisijaisesti
                // `this`-olion tiedoista.
                // Mikäli tätä ei ole, käytetään
                // alkuperäisen datan sisältämää arvoa.
                if (this.hasOwnProperty(
                  vierasavain_id
                ))
                  return document.data[vierasavain]?.[
                    this[vierasavain_id]
                  ];
                else
                  return document.data[vierasavain]?.[
                    arvo[vierasavain_id]
                  ];
              },
              enumerable: arvo.hasOwnProperty(
                vierasavain_id
              ),
              configurable: false
            }
          );
        }
        else
          this._tulkitseVierasavaimet(arvo);
      }
    },

    toiminto: function (data) {
      data.toiminto_id = ++this.toiminto_id;
      return new Promise(function (vastaus, virhe) {
        this.toimintojono[data.toiminto_id] = {
          vastaus: typeof vastaus === "function"? vastaus : function () {},
          virhe: typeof virhe === "function"? virhe : function (data) {
            alert(data.virhe ?? "Tuntematon palvelinvirhe");
          }
        }
        if (this.yhteys?.readyState === 1) {
          this._lahetaData(data);
        }
        else {
          // Jätä sanoma jonoon, mikäli yhteyttä ei ole.
          this.lahetysjono.push(data);
        }
      }.bind(this));
    },

    _patkiOsiin: function (jono, koko) {
      const kpl = Math.ceil(jono.length / koko);
      const osat = new Array(kpl);
      for (let i = 0, o = 0; i < kpl; ++i, o += koko) {
        osat[i] = jono.substr(o, koko);
      }
      return osat;
    },

    yhdistaUudelleen: function () {
      return this._avaaYhteys();
    },

    /*
     * Vie `this.__vietavaData` JSON-tiedostoon.
     */
    vieData: function () {
      var json = JSON.stringify(this.__vietavaData);
      var a = document.createElement("a");
      document.body.appendChild(a);
      a.style = "display: none";
      a.href = window.URL.createObjectURL(new Blob(
        [json],
        {type: "application/json"}
      ));
      a.download = "data.json";
      a.click();
      window.URL.revokeObjectURL(a.href);
    },

    /*
     * Tuo `document.data` JSON-tiedostosta.
     */
    tuoData: function () {
      var input = document.createElement("input");
      document.body.appendChild(input);
      input.type = "file";
      input.style = "display: none";
      input.onchange = function (e) {
        let fr = new FileReader();
        fr.onload = function () {
          document.data = JSON.parse(fr.result);
          document.synkroni._tulkitseVierasavaimet(document.data);
          document.dispatchEvent(new Event("yhteys-avattu"));
          document.dispatchEvent(new CustomEvent(
            "yhteys-alustettu",
            {detail: {uusi: true}}
          ));
          document.dispatchEvent(new Event("data-paivitetty"));
        };
        fr.readAsBinaryString(e.target.files[0]);
      };
      input.click();
    }
  });

  document.synkroni = new Synkroni();
})();
