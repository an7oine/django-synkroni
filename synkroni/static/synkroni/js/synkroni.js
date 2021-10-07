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
    this.komennot = {};
    this.yhteys = null;
    this.komento_id = 0;
    this.lahetysjono = [];

    this.kattely = JSON.parse(
      kattely? kattely.replace(/'/g, '"') : "{}"
    );
    this.data = JSON.parse(
      alkutila? alkutila.replace(/'/g, '"') : "{}"
    );

    if (window.JSONPatcherProxy) {
      this.tarkkailija = new JSONPatcherProxy(this.data);
      this.data = this.tarkkailija.observe(
        true, this._lahtevaMuutos.bind(this)
      );
    }

    this._avaaYhteys();
  }

  Object.assign(Synkroni.prototype, {
    MAKSIMIDATA: 1024 * 1024,

    _avaaYhteys: function () {
      this.yhteys = new WebSocket(this.osoite, this.protokolla);
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
      this.komento({
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
        new Event("yhteys-katkaistu")
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
      if (data.hasOwnProperty("virhe")) {
        alert(data.virhe || "Tuntematon palvelinvirhe");
      }
      else if (data.hasOwnProperty("komento_id")) {
        this.komennot[data.komento_id]?.(data);
        delete this.komennot[data.komento_id];
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
      jsonpatch.apply(this.data, p);
      this.tarkkailija?.resume?.();
      document.dispatchEvent(
        new Event("data-paivitetty")
      );
    },

    komento: function (data, vastaus) {
      data.komento_id = ++this.komento_id;
      if (typeof vastaus === "function") {
        this.komennot[data.komento_id] = vastaus;
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
