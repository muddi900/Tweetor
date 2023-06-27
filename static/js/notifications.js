   // notifications.js

   const eventSource = new EventSource('/notifications');

   eventSource.onmessage = function(event) {
       const notification = event.data;
       // Handle the received notification (e.g., display a notification message)
       const notificationList = document.getElementById('notification-list');
       const newNotification = document.createElement('li');
       newNotification.textContent = notification;
       notificationList.appendChild(newNotification);
   };