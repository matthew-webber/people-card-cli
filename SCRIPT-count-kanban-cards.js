(function() {
  const title = window.prompt("Enter the swim lane title (e.g., 'Design In Progress'):");
  if (!title) {
    console.log("No title entered.");
    return;
  }

  const columns = document.querySelectorAll('.taskBoardColumn');
  for (const col of columns) {
    const heading = col.querySelector('.columnTitle h3');
    if (heading && heading.textContent.trim() === title) {
      const count = col.querySelectorAll('.taskBoardCard').length;
      console.log(`Swim lane "${title}" has ${count} taskBoardCard(s).`);
      return;
    }
  }

  console.log(`No swim lane found with title "${title}".`);
})();