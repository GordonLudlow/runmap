// worker.js for runmap

self.importScripts("./lib/sax/lib/sax.js")

var strict = true, // set to false for html-mode
    parser = sax.parser(strict);

var runs = [];
var bounds = [];

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
                postMessage({type: "remove", index: i});
                run.state = kNotDrawn;
            }
        }
    });
    console.log("On screen count = " + onScreen.length);
    // Depending on the count and whether or not we're at max zoom, drawn lines, polylines or cluster circles
    // TODO: Add max zoom message
    // TODO: Cluster circles
    // TODO: Draw something when there's no on screen runs.  Maybe arrows with numbers showing how many runs are in which direction.
    if (onScreen.length < 100) {
        // Load individual runs
        onScreen.forEach(function(i) {
            if (runs[i].state != kPolyLine) {
                runs[i].state = kPolyLine;
                // Load the track data
                xmlhttp=new XMLHttpRequest();
                xmlhttp.open("GET", runs[i[.name);
                xmlhttp.onreadystatechange = function() {
                if (xmlhttp.readyState == 4) { // complete 
                    if (xmlhttp.status == 200) { // OK
                    }
                }
            }
        });
    }
    else {
        onScreen.forEach(function(i) {
            if (runs[i].state != kLine) {
                postMessage({type: "line", index: i, line: runs[i].line});
                runs[i].state = kLine;
            }
        });
    }
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
                        console.log("attribute " + attr.name + " = " + attr.value);
                    };
                    parser.onend = function () {
                        // parser stream is done, and ready to have more stuff written to it.
                        //console.log("The End");
                        if (!(Object.keys(obj).length === 0 && obj.constructor === Object)) {
                            obj.state = kNotDrawn;                        
                            runs.push(obj);
                        }
                        console.log(runs);
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
        //console.log(bounds);
        // a string of the form "lat_lo,lng_lo,lat_hi,lng_hi" for this bounds, where "lo" corresponds to the southwest corner of the bounding box, while "hi" corresponds to the northeast corner of that box.
    }    
}

