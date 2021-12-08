(function () {
  /*
   * Luo Websocket-palvelinyhteys.
   */
  const {
    websocket,
    protokolla,
    kattely,
    alkutila
  } = document.currentScript.dataset;

  function Synkroni() {
    this.osoite = websocket;
    this.protokolla = JSON.parse(protokolla ?? "null");
    this.toimintojono = {};
    this.yhteys = null;
    this.toiminto_id = 0; // Seuraava käyttämätön toiminto-id.
    this.lahetysjono = [];
    this.kattely = JSON.parse(
      kattely? kattely.replace(/'/g, '"') : "{}"
    );

    // Alusta `document.toiminto`.
    document.toiminto = this.toiminto.bind(this);

    // Alusta `document.data`.
    let data = JSON.parse(
      alkutila? alkutila.replace(/'/g, '"') : "{}"
    );
    if (window.JSONPatcherProxy) {
      this.tarkkailija = new JSONPatcherProxy(data);
      data = this.tarkkailija.observe(
        true, this._lahtevaMuutos.bind(this)
      );
    }
    document.data = data;

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
      }, function () {
        const uusi = this.kattely.uusi;
        if (uusi) {
          delete this.kattely.uusi;
        }
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
      if (e.code > 1001)
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
      else if (data.hasOwnProperty("virhe")) {
        alert(data.virhe || "Tuntematon palvelinvirhe");
      }
      else if (data.hasOwnProperty("toiminto_id")) {
        this.toimintojono[data.toiminto_id]?.(data);
        delete this.toimintojono[data.toiminto_id];
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
      this.tarkkailija?.resume?.();
      document.dispatchEvent(
        new Event("data-paivitetty")
      );
    },

    toiminto: function (data, vastaus) {
      data.toiminto_id = ++this.toiminto_id;
      if (typeof vastaus === "function") {
        this.toimintojono[data.toiminto_id] = vastaus;
      }
      if (this.yhteys?.readyState === 1) {
        this._lahetaData(data);
      }
      else {
        // Jätä sanoma jonoon, mikäli yhteyttä ei ole.
        this.lahetysjono.push(data);
      }
    },

    _patkiOsiin: function (jono, koko) {
      const kpl = Math.ceil(jono.length / koko);
      const osat = new Array(kpl);
      for (let i = 0, o = 0; i < kpl; ++i, o += koko) {
        osat[i] = jono.substr(o, koko);
      }
      return osat;
    }
  });

  document.synkroni = new Synkroni();
})();
