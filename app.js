// Load bills from JSON file
fetch('bills.json')
  .then(response => response.json())
  .then(data => {
    const tracker = document.getElementById('tracker');

    // Create HTML for each bill and insert into tracker div
    data.forEach(bill => {
      let silentmajorityLink = '';
      if (bill.silentmajority_url) {
        silentmajorityLink = `<a href="${bill.silentmajority_url}" target="_blank">Read analysis on Silent Majority 420</a>`;
      }

      const billHtml = `
        <div class="bill">
          <div class="date">${bill.date}</div>
          <div class="title">
            <a href="${bill.url}" target="_blank">${bill.id}</a>
          </div>
          <div class="description">
            ${bill.description}
            ${silentmajorityLink}
          </div>
        </div>
      `;
      tracker.insertAdjacentHTML('beforeend', billHtml);
    });
  })
  .catch(error => {
    console.error('Error loading bills:', error);
  });
