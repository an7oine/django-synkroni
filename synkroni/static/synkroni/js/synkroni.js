(function () {
  function patkiOsiin(jono, koko) {
    const kpl = Math.ceil(jono.length / koko);
    const osat = new Array(kpl);
    for (let i = 0, o = 0; i < kpl; ++i, o += koko) {
      osat[i] = jono.substr(o, koko);
    }
    return osat;
  }

  var Synkroni = function (osoite, kattely, data) {
    this.osoite = osoite;
    this.kattely = kattely;
    this.komennot = {};
    this.yhteys = null;
    this.komento_id = 0;
    this.tarkkailija = new JSONPatcherProxy(data || {});
    this.data = this.tarkkailija.observe(
      true, this._lahtevaMuutos.bind(this)
    );
    this.lahetysjono = [];
    this._avaaYhteys();
    // Kuuntelijat.
    this.yhteysAvattu = null;
    this.yhteysKatkaistu = null;
  };

  Object.assign(Synkroni.prototype, {
    MAKSIMIDATA: 1024 * 1024,

    _avaaYhteys: function () {
      this.yhteys = new WebSocket(this.osoite);
      Object.assign(this.yhteys, {
        onopen: this._yhteysAvattu.bind(this),
        onmessage: this._viestiVastaanotettu.bind(this),
        onclose: this._yhteysKatkaistu.bind(this),
      });
    },
    _yhteysAvattu: function (e) {
      if (typeof this.kattely === "function") {
        this._lahetaData(this.kattely(e));
      }
      else if (this.kattely) {
        this._lahetaData(this.kattely);
      }
      for (lahteva_sanoma of this.lahetysjono) {
        this._lahetaData(lahteva_sanoma);
      }
      this.lahetysjono = [];

      // Lähetä tieto mahdolliselle kuuntelijalle.
      if (typeof this.yhteysAvattu === "function")
        this.yhteysAvattu(e);
    },
    _yhteysKatkaistu: function (e) {
      // Lähetä tieto mahdolliselle kuuntelijalle.
      if (typeof this.yhteysKatkaistu === "function")
        this.yhteysKatkaistu(e);

      // Poista aiempi yhteys.
      this.yhteys = null;

      // Yritä yhteyden muodostamista uudelleen automaattisesti,
      // mikäli yhteys katkesi muusta kuin käyttäjästä
      // johtuvasta syystä.
      if (e.code > 1001)
        window.setTimeout(this._avaaYhteys.bind(this), 100);
    },
    _viestiVastaanotettu: function (e) {
      let data = JSON.parse(e.data);
      if (data.hasOwnProperty("virhe")) {
        alert(data.virhe || "Tuntematon palvelinvirhe");
      }
      else if (data.hasOwnProperty("komento_id")) {
        this.komennot[data.komento_id](data);
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
        let osat = patkiOsiin(
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
      this.tarkkailija.pause();
      jsonpatch.apply(this.data, p);
      this.tarkkailija.resume();
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
    }
  });

  window.Synkroni = Synkroni;
})();
