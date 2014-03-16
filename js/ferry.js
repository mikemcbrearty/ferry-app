var map = L.map('map', {
    center: [40.675, -74.035],
    zoom: 13,
    touchZoom: false,
    scrollWheelZoom: false,
    zoomControl: false,
});

L.tileLayer('http://otile4.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

var ferry_layer = L.layerGroup();
ferry_layer.addTo(map);

var geojsonMarkerOptions = {
    radius: 6,
    fillColor: "#ff8c00",
    color: "#000",
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8
};
var ptToLayer = function(feature, latlng) {
  return L.circleMarker(latlng, geojsonMarkerOptions);
};
var objToGeojson = function(obj) {
  return { "type": "Feature",
           "geometry": { "type": "Point", "coordinates": [obj.longitude, obj.latitude] },
           "properties": { "id": "cover", "zoom": 4, "mmsi": obj.mmsi } };
};
var updateFerryLayer = function(arr) {
    var obj = arr[0];
    ferry_layer.eachLayer(function(layer){
        if (layer.toGeoJSON().features[0].properties.mmsi === obj.mmsi)
            ferry_layer.removeLayer(layer);
    });
    var layer = L.geoJson(objToGeojson(obj), { pointToLayer: ptToLayer });
    ferry_layer.addLayer(layer);
};

var wrapP = function(txt){ return "<p>"+txt+"</p>"; }
var msgToStr = function(arr) {
    ferries = {
        366952890: "Spirit of America",
        366952870: "Sen. John J Marchi",
        366952790: "Guy V Molinari",
        367000140: "Samuel I Newhouse",
        367000150: "Andrew J Barberi",
        367000190: "John F Kennedy",
        367000110: "John Noble",
        367000120: "Alice Austen",
    };

    var obj = arr[0];
    var d = new Date(obj.last_update);
    return wrapP(ferries[obj.mmsi]+":<br> "+obj.latitude+"N "+(-obj.longitude)+"W "+moment(d).format("h:mm a"));
}

// WEB SOCKETS

var messageContainer = document.getElementById("messages");
var viewportWidth = function(){
    var w = window,
        e = document.documentElement,
        g = document.getElementsByTagName("body")[0],
        x = w.innerWidth || e.clientWidth || g.clientWidth;
    return x;
}();
var numUpdatesToShow = (viewportWidth > 640) ? 5 : 1;
var openWebSocket = function() {
    if ("WebSocket" in window) {
        var ws = new WebSocket("ws://localhost:8888/");
        ws.onopen = function() {};
        ws.onmessage = function (e) {
            var msg = JSON.parse(e.data);
            updateFerryLayer(msg);
            var slicePriorMsgs = messageContainer.innerHTML.slice(3, -4).split("</p><p>").slice(0,numUpdatesToShow-1).map(wrapP);
            messageContainer.innerHTML = [msgToStr(msg)].concat(slicePriorMsgs).join("");
        };
        ws.onclose = function() {
            messageContainer.innerHTML = "Connection is closed...";
        };
    } else {
        messageContainer.innerHTML = "WebSocket NOT supported by your Browser!";
    }
}
openWebSocket();