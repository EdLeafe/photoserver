var blankType = "{type}";
var blankSelect = "-Select " + blankType + "-";

function removeComparator(div) {
  var kids = div.children;
  for (i = kids.length - 1; i >= 2; i--) {
    kids[i].remove()
  }
}

function removeValueObj(div) {
  var kids = div.children;
  for (i = kids.length - 1; i >= 3; i--) {
    kids[i].remove()
  }
}

function removeRow(row) {
  var div = document.getElementById("newdiv" + row);
  div.remove();
}

function addTextField(div, row) {
  removeValueObj(div);
  var textField = document.createElement("input");
  textField.setAttribute("type", "text");
  textField.setAttribute("id", "value" + row);
  textField.setAttribute("name", "value" + row);
  textField.setAttribute("value", "");
  textField.addEventListener(("blur"), function() {
    previewRules();
  })
  return textField;
}

function addAutoCompleteTextField(div, row) {
  removeValueObj(div);
  var textField = document.createElement("input");
  textField.setAttribute("type", "text");
  textField.setAttribute("class", "autocomplete");
  textField.setAttribute("id", "value" + row);
  textField.setAttribute("name", "value" + row);
  textField.value = "";
  textField.addEventListener(("blur"), function() {
    previewRules();
  })
  autocomplete(textField, keywords);
  return textField;
}

function addDatePickerTextField(div, row) {
  removeValueObj(div);
  var textField = document.createElement("input");
  textField.setAttribute("type", "date");
  textField.setAttribute("class", "datepicker");
  textField.setAttribute("id", "value" + row);
  textField.setAttribute("name", "value" + row);
  var today = new Date()
//  textField.setAttribute("value", today.toISOString().split("T")[0]);
  textField.addEventListener(("blur"), function() {
    previewRules();
  })
  return textField;
}

function addAlbumPicker(div, row) {
  removeValueObj(div);
  var selectObj = document.createElement("select");
  selectObj.setAttribute("id", "value" + row);
  selectObj.setAttribute("name", "value" + row);
  var opt = document.createElement("option");
  opt.setAttribute("id", "albumopt-select-" + row);
  opt.setAttribute("name", "albumopt-select-" + row);
  opt.innerText = blankSelect.replace(blankType, "Album");
  selectObj.appendChild(opt);
  for (i = 0; i <= albumNames.length; i++) {
    opt = document.createElement("option");
    opt.setAttribute("id", "albumopt" + row + "-" + i);
    opt.setAttribute("name", "albumopt" + row + "-" + i);
    opt.setAttribute("value", albumIds[i]);
    opt.innerText = albumNames[i];
    selectObj.appendChild(opt);
  }
  selectObj.addEventListener(("blur"), function() {
    previewRules();
  })
  selectObj.addEventListener(("change"), function() {
    previewRules();
  })
  return selectObj;
}

function addOptsForField(div, comp, field, row, val) {
  var optNames = [];
  var row = div.getAttribute("rownumber");
  var valueObj = null;
  var i;
  switch (field) {
    case "(":
      break;
    case ")":
      break;
    case "keywords":
      optNames = ["Must contain", "May contain", "Must not contain"];
      valueObj = addAutoCompleteTextField(div, row);
      break;
    case "name":
      optNames = ["Equals", "Starts with", "Ends with", "Contains"];
      valueObj = addTextField(div, row);
      break;
    case "orientation":
      optNames = ["Horizontal", "Vertical", "Square"];
      removeValueObj(div);
      break;
    case "created":
      optNames = ["Equals", "Before", "After", "On or before", "On or after"];
      valueObj = addDatePickerTextField(div, row);
      break;
    case "year":
      optNames = [];
      var currentDate = new Date();
      var currentYear = currentDate.getFullYear();
      for (i = currentYear; i >= 1969; i--) {
        optNames.push(i);
      }
      removeValueObj(div);
      break;
    case "album":
      optNames = ["Is a member of", "Is not a member of"];
      valueObj = addAlbumPicker(div, row);
      break;
  }
  if (valueObj !== null) {
    var valueDiv = document.createElement("div");
    valueDiv.setAttribute("id", "valueselectdiv" + row);
    valueDiv.setAttribute("class", "three columns");
    valueDiv.appendChild(valueObj);
    div.appendChild(valueDiv);
    if ( valueObj.value === "" || valueObj.value === null ) {
      valueObj.value = val;
    }
    valueObj.focus();
  }
  for (i = 0; i < optNames.length; i++) {
    opt = document.createElement("option");
    opt.setAttribute("id", "compopt" + row + "-" + i);
    opt.setAttribute("name", "compopt" + row + "-" + i);
    opt.setAttribute("value", optNames[i]);
    opt.innerText = optNames[i];
    comp.appendChild(opt);
  }
  comp.addEventListener(("blur"), function() {
    previewRules();
  })
  comp.addEventListener(("change"), function() {
    previewRules();
  })
}

function setComparator(field, div, comp, val) {
  removeComparator(div);

  var row = div.getAttribute("rownumber");
  var compSelectDiv = document.createElement("div");
  compSelectDiv.setAttribute("id", "compselectdiv" + row);
  compSelectDiv.setAttribute("class", "two columns");
  div.appendChild(compSelectDiv);

  compObj = document.createElement("select");
  compObj.setAttribute("id", "comp" + row);
  compObj.setAttribute("name", "comp" + row);
  compSelectDiv.appendChild(compObj);
  addOptsForField(div, compObj, field, row, val);
  if (comp !== undefined) {
    compObj.value = comp;
  }
}

function addRuleRow(field, comp, val) {
  var grp = document.getElementById("controlGroup");
  var currRuleRow = document.maxRules++;
  /*create a DIV element that will contain the items (values):*/
  var fldNames = ["(", ")", "keywords", "name", "orientation", "created", "year", "album"]
  var newdiv = document.createElement("div");
  newdiv.setAttribute("id", "newdiv" + currRuleRow);
  newdiv.setAttribute("class", "twelve columns");
  newdiv.setAttribute("rownumber", currRuleRow);
  addMinus(newdiv);
    /*addJoin(newdiv, currRuleRow);*/
  grp.appendChild(newdiv);

  var fieldSelectDiv = document.createElement("div");
  fieldSelectDiv.setAttribute("id", "fieldselectdiv" + currRuleRow);
  fieldSelectDiv.setAttribute("class", "two columns");
  newdiv.appendChild(fieldSelectDiv);
  var dd = document.createElement("select");
  dd.setAttribute("id", "field" + currRuleRow);
  dd.setAttribute("name", "field" + currRuleRow);
  fieldSelectDiv.appendChild(dd);

  var opt = document.createElement("option");
  var thisfield = blankSelect.replace(blankType, "Field");
  opt.setAttribute("id", "fldopt-select-" + currRuleRow);
  opt.setAttribute("name", "fldopt-select-" + currRuleRow);
  opt.innerText = thisfield;
  dd.appendChild(opt);
  var i;
  for (i = 0; i < fldNames.length; i++) {
    thisfield = fldNames[i];
    opt = document.createElement("option");
    opt.setAttribute("id", "fldopt" + currRuleRow + "-" + thisfield);
    opt.setAttribute("name", "fldopt" + currRuleRow + "-" + thisfield);
    opt.setAttribute("value", thisfield);
    opt.innerText = thisfield;
    if (field === thisfield) {
      opt.selected = true;
    }
    dd.appendChild(opt);
  }
  dd.addEventListener(("change"), function() {
    setComparator(dd.value, newdiv);
  })
  if (comp !== undefined) {
    setComparator(field, newdiv, comp, val);
  }
}

function previewRules() {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/albums/smart_calculate");
  xhr.onload = function(event){ 
    var resp = event.target.response;
    var resp_obj = JSON.parse(resp);
    var num = Object.keys(resp_obj).length;
    var smartresult = document.getElementById("smartresult");
    smartresult.innerText = num + " images match";
  };
  var formData = new FormData(document.getElementById("update_album_rules")); 
  xhr.send(formData);
}

document.addEventListener("DOMContentLoaded", function() {
  var btn = document.getElementById("addbutton");
  btn.addEventListener(("click"), function(e) {
    addRuleRow();
  })
  var prv = document.getElementById("previewbutton");
  prv.addEventListener(("click"), function(e) {
    previewRules();
  })
//  var elems = document.querySelectorAll(".datepicker");
//  var instances = M.Datepicker.init(elems, options={"format":"yyyy-mm-dd", "selectMonths": true, "autoClose": true});
});
