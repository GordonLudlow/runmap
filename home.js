// worker.js for runmap, this version is for everything a mile from home

// A mile north of home is 47° 30′ 31″ N, 122° 09′ 58″ W
// A mile east  of home is 47° 29′ 39″ N, 122° 08′ 41″ W
// A mile south of home is 47° 28′ 47″ N, 122° 09′ 58″ W
// A mile west  of home is 47° 29′ 39″ N, 122° 11′ 14″ W

self.importScripts("./lib/sax/lib/sax.js")

var strict = true, // set to false for html-mode
    parser = sax.parser(strict);

var runs = [];
var bounds = [];
var gpxhttp = [];
var maxZoom = false;

// run states
const kNotDrawn = 0;
const kCloud = 1;
const kLine = 2;
const kPolyLine = 4;
  
// Some XMLHttpRequest hooey
if (typeof XMLHttpRequest === "undefined") {
  XMLHttpRequest = function () {
    try { return new ActiveXObject("Msxml2.XMLHTTP.6.0"); }
    catch (e) {}
    try { return new ActiveXObject("Msxml2.XMLHTTP.3.0"); }
    catch (e) {}
    try { return new ActiveXObject("Microsoft.XMLHTTP"); }
    catch (e) {}
    // Microsoft.XMLHTTP points to Msxml2.XMLHTTP and is redundant
    throw new Error("This browser does not support XMLHttpRequest.");
  };
}

intersects = function(aabb, bounds) {
    // aabb is of the form [[latMin, longMin], [latMax, longMax]]
    let min = 0;
    let max = 1;
    let lat = 0;
    let lng = 1;
    // bounds is of the form [latMin, longMin, latMax, longMax]
    let latMin = 0;
    let longMin = 1;
    let latMax = 2;
    let longMax = 3;
    
    return (aabb[min][lat] <= bounds[latMax] 
         && bounds[latMin] <= aabb[max][lat]
         && aabb[min][lng] <= bounds[longMax] 
         && bounds[longMin] <= aabb[max][lng]);
}

updateRunStates = function() {
    let onScreen = [];
    runs.forEach(function(run, i) {
        if (intersects(run.aabb, bounds)) {
            onScreen.push(i);
        }
        else {
            if (run.state != kNotDrawn) {
                // Will have to remove it from a cloud, assume kLine or kPolyLine for now
                console.log("Removing " + runs[i].name);
                postMessage({type: "remove", index: i});
                run.state = kNotDrawn;
            }
        }
    });
    console.log("On screen count = " + onScreen.length);
    // In this version, we draw all the details
    { //if (onScreen.length < 50 || maxZoom) { 
        // Load individual runs
        onScreen.forEach(function(i) {
            if (runs[i].state != kPolyLine) {
                if (runs[i].state == kNotDrawn) {
                    // Give it a line while waiting for the load
                    postMessage({type: "line", index: i, line: runs[i].line, name: runs[i].name});
                }
                runs[i].state = kPolyLine;
                // Load the track data
                console.log("Opening " + runs[i].name);
                gpxhttp[i]=new XMLHttpRequest();
                //gpxhttp[i].open("GET", "./runs/" + runs[i].name + ".gz");
                gpxhttp[i].open("GET", "./runs/" + runs[i].name);
                gpxhttp[i].onreadystatechange = function(i) {
                    return function() {
                        if (gpxhttp[i].readyState == 4) { // complete 
                            if (gpxhttp[i].status == 200) { // OK
                                if (runs[i].state != kPolyLine) {
                                    console.log("Ignoring " + runs[i].name);
                                    return;  // the world has moved on
                                }
                                let points = [];
                                let lat = null;
                                let lng = null;
                                let tag = null;
                                parser.onerror = function (e) {
                                  // an error happened.
                                  console.log("Parsing error in " + runs[i].name);
                                  console.log(e);
                                };
                                parser.ontext = function (t) {
                                    // got some text.  t is the string of text.
                                    //console.log("Got text: " + t);
                                    if (t.trim().length) {
                                        if (tag === 'LongitudeDegrees') {
                                            lng = t;
                                        }
                                        else if (tag === 'LatitudeDegrees') {
                                            lat = t;
                                        }
                                        if (lat != null && lng != null) {
                                            points.push([lat, lng]);
                                            lat = null;
                                            lng = null;
                                        }
                                    }
                                };
                                parser.onopentag = function (node) {
                                    // opened a tag.  node has "name" and "attributes"
                                    //console.log("Open tag: " + node.name);
                                    //console.log(node.attributes);        
                                    tag = node.name;
                                    if (tag === 'trkpt') {
                                        if (node.attributes.hasOwnProperty('lat')) {
                                            points.push([node.attributes.lat, node.attributes.lon]);
                                        }
                                    }
                                };
                                parser.onattribute = function (attr) {
                                    // an attribute.  attr has "name" and "value"
                                    //console.log("attribute " + attr.name + " = " + attr.value);
                                    if (tag === 'trkpt') {
                                        if (attr.name === 'lat') {
                                            lat = attr.value;
                                        }
                                        else if (attr.name === 'lon') {
                                            lng = attr.value;
                                        }
                                        if (lat != null && lng != null) {
                                            points.push([lat, lng]);
                                            lat = null;
                                            lng = null;
                                        }
                                    }
                                };
                                parser.onend = function () {
                                    // parser stream is done, and ready to have more stuff written to it.
                                    //console.log("The End");
                                    //console.log(points);
                                    if (runs[i].state != kPolyLine) {
                                        console.log("Ignoring " + runs[i].name);
                                        return;  // the world has moved on
                                    }                                    
                                    postMessage({type: "polyline", index: i, line: points, name: runs[i].name});                                    
                                    points = [];
                                };

                                parser.write(gpxhttp[i].responseText).close();
                                gpxhttp[i]=null;
                            }
                            else {
                                console.log(gpxhttp[i]);
                            }
                        }
                    }
                }(i);
                gpxhttp[i].send();
            }
        });
    }
    /*
    else {
        onScreen.forEach(function(i) {
            if (runs[i].state != kLine) {
                postMessage({type: "line", index: i, line: runs[i].line, name: runs[i].name});
                runs[i].state = kLine;
            }
        });
    }
    */
};

onmessage = function(message) {
    if (message.data[0] == "initialize") {
        xmlhttp=new XMLHttpRequest();
        xmlhttp.open("GET","allruns.xml?time=" + Date.now());
        xmlhttp.onreadystatechange = function() {
            if (xmlhttp.readyState == 4) { // complete 
                if (xmlhttp.status == 200) { // OK
                    let tag;
                    let obj = {};
                    parser.onerror = function (e) {
                      // an error happened.
                      console.log("Parsing error in allruns.xml");
                      console.log(e);
                    };
                    parser.ontext = function (t) {
                        // got some text.  t is the string of text.
                        //console.log("Got text: " + t);
                        if (tag === 'name') {
                            obj.name = t;
                        }
                        else if (tag === 'aabb') {
                            obj.aabb = JSON.parse(t);
                        }
                        else if (tag === 'line') {
                            obj.line = JSON.parse(t);
                        }
                    };
                    parser.onopentag = function (node) {
                        // opened a tag.  node has "name" and "attributes"
                        //console.log("Open tag: " + node.name);
                        tag = node.name;
                        if (tag === 'file') {
                            if (!(Object.keys(obj).length === 0 && obj.constructor === Object)) {
                                obj.state = kNotDrawn;
                                runs.push(obj);
                                obj = {};
                            }
                        }                        
                    };
                    parser.onattribute = function (attr) {
                        // an attribute.  attr has "name" and "value"
                        //console.log("attribute " + attr.name + " = " + attr.value);
                    };
                    parser.onend = function () {
                        // parser stream is done, and ready to have more stuff written to it.
                        //console.log("The End");
                        if (!(Object.keys(obj).length === 0 && obj.constructor === Object)) {
                            obj.state = kNotDrawn;                        
                            runs.push(obj);
                        }
                        //console.log(runs);
                        if (bounds.length) {
                            // We already got the initial map bounds, do the thing
                            updateRunStates();
                        }
                    };

                    parser.write(xmlhttp.responseText).close();
                }
            }
        };
        xmlhttp.send();
        return;
    }
    if (message.data[0] == "bounds") {    
        bounds = JSON.parse('[' + message.data[1] + ']');
        if (runs.length) {
            updateRunStates();
        }
        return;
    }
    if (message.data[0] == "maxZoom") {
        maxZoom = message.data[1];
    }
}

