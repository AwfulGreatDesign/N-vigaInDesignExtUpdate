var csInterface = new CSInterface();

var openButton = document.querySelector("#open-button");
openButton.addEventListener("click", openDoc);

function openDoc() {
	//console.log("I can't believe you clicked!");
	var path = csInterface.getSystemPath(SystemPath.EXTENSION);
	csInterface.evalScript("openDocument('" + path + "')");
}